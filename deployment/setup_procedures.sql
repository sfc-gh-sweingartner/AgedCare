-- =============================================================================
-- DRI Intelligence - Stored Procedures
-- =============================================================================
-- Run after setup_database.sql to create required stored procedures
--
-- Procedures:
--   1. CALCULATE_DRI_SCORES - Recalculates DRI scores for all residents
--   2. DRI_TIME_PROCESSOR - Daily processor for expiring indicators
--   3. DRI_EVENT_PROCESSOR - Processes indicator confirmations/rejections
--
-- Usage:
--   snow sql -f deployment/setup_procedures.sql -c <connection_name>
-- =============================================================================

-- Use the target database/schema
-- SET database_name = 'AGEDCARE_TEST';
-- SET schema_name = 'DRI';

-- =============================================================================
-- 1. CALCULATE_DRI_SCORES
-- =============================================================================
-- Recalculates DRI scores for all residents based on active deficits

CREATE OR REPLACE PROCEDURE CALCULATE_DRI_SCORES()
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS '
BEGIN
    MERGE INTO DRI_DEFICIT_SUMMARY AS target
    USING (
        SELECT
            ds.RESIDENT_ID,
            CURRENT_TIMESTAMP() AS LOAD_TIMESTAMP,
            COUNT(*) / 33.0 AS DRI_SCORE,
            CASE
                WHEN COUNT(*) / 33.0 <= 0.2 THEN ''Low''
                WHEN COUNT(*) / 33.0 <= 0.4 THEN ''Medium''
                WHEN COUNT(*) / 33.0 <= 0.6 THEN ''High''
                ELSE ''Very High''
            END AS SEVERITY_BAND
        FROM DRI_DEFICIT_STATUS ds
        WHERE ds.DEFICIT_STATUS = ''ACTIVE''
        GROUP BY ds.RESIDENT_ID
    ) AS source
    ON target.RESIDENT_ID = source.RESIDENT_ID
    WHEN MATCHED THEN UPDATE SET
        target.DRI_SCORE = source.DRI_SCORE,
        target.SEVERITY_BAND = source.SEVERITY_BAND,
        target.LOAD_TIMESTAMP = source.LOAD_TIMESTAMP
    WHEN NOT MATCHED THEN INSERT (RESIDENT_ID, LOAD_TIMESTAMP, DRI_SCORE, SEVERITY_BAND)
        VALUES (source.RESIDENT_ID, source.LOAD_TIMESTAMP, source.DRI_SCORE, source.SEVERITY_BAND);

    RETURN ''DRI scores updated'';
END;
';

-- =============================================================================
-- 2. DRI_TIME_PROCESSOR
-- =============================================================================
-- Daily processor that:
--   - Expires indicators past their expiry date
--   - Re-evaluates threshold-based indicators
--   - Clears expired rejections
--   - Recalculates DRI scores for affected residents

CREATE OR REPLACE PROCEDURE DRI_TIME_PROCESSOR(
    P_CLIENT_SYSTEM_KEY VARCHAR DEFAULT NULL,
    P_TRIGGERED_BY VARCHAR DEFAULT 'MANUAL'
)
RETURNS VARIANT
LANGUAGE JAVASCRIPT
EXECUTE AS CALLER
AS '
var runId = snowflake.createStatement({sqlText: "SELECT UUID_STRING() as ID"}).execute();
runId.next();
var vRunId = runId.getColumnValue("ID");

var startTime = new Date();
var indicatorsExpired = 0;
var indicatorsRenewed = 0;
var residentsAffected = new Set();
var details = [];

try {
    // STEP 1: Expire indicators past their expiry date
    var expireStmt = snowflake.createStatement({
        sqlText: `UPDATE DRI_DEFICIT_STATUS
                  SET DEFICIT_STATUS = ''EXPIRED'', LOAD_TIMESTAMP = CURRENT_TIMESTAMP()
                  WHERE DEFICIT_STATUS = ''ACTIVE''
                  AND DEFICIT_EXPIRY_DATE IS NOT NULL
                  AND DEFICIT_EXPIRY_DATE < CURRENT_DATE()`
    });
    var expireResult = expireStmt.execute();
    indicatorsExpired = expireStmt.getNumRowsAffected();

    // Also expire in clinical decisions
    var expireDecStmt = snowflake.createStatement({
        sqlText: `UPDATE DRI_CLINICAL_DECISIONS
                  SET STATUS = ''EXPIRED''
                  WHERE STATUS = ''ACTIVE''
                  AND EXPIRY_DATE IS NOT NULL
                  AND EXPIRY_DATE < CURRENT_DATE()`
    });
    expireDecStmt.execute();

    details.push({step: "expire_indicators", count: indicatorsExpired});

    // STEP 2: Re-evaluate threshold-based indicators
    var thresholdRulesStmt = snowflake.createStatement({
        sqlText: `SELECT DEFICIT_ID, DEFICIT_TYPE,
                  COALESCE(EXPIRY_DAYS, 0) as EXPIRY_DAYS,
                  COALESCE(LOOKBACK_DAYS_HISTORIC, 365) as LOOKBACK_DAYS,
                  RULES_JSON
                  FROM DRI_RULES
                  WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE`
    });
    var thresholdRules = thresholdRulesStmt.execute();

    var thresholdDeficits = [];
    while (thresholdRules.next()) {
        var rulesJson = thresholdRules.getColumnValue("RULES_JSON");
        var threshold = 1;
        if (rulesJson && rulesJson[0] && rulesJson[0].threshold) {
            threshold = parseInt(rulesJson[0].threshold);
        }
        if (threshold > 1) {
            thresholdDeficits.push({
                deficit_id: thresholdRules.getColumnValue("DEFICIT_ID"),
                deficit_type: thresholdRules.getColumnValue("DEFICIT_TYPE"),
                expiry_days: thresholdRules.getColumnValue("EXPIRY_DAYS"),
                lookback_days: thresholdRules.getColumnValue("LOOKBACK_DAYS"),
                threshold: threshold
            });
        }
    }

    // For each threshold deficit, check if any residents now fall below threshold
    for (var i = 0; i < thresholdDeficits.length; i++) {
        var def = thresholdDeficits[i];
        var lb = def.lookback_days === "all" ? 9999 : parseInt(def.lookback_days);

        var checkStmt = snowflake.createStatement({
            sqlText: `SELECT ds.RESIDENT_ID, COUNT(occ.OCCURRENCE_ID) as OCC_COUNT
                      FROM DRI_DEFICIT_STATUS ds
                      LEFT JOIN DRI_INDICATOR_OCCURRENCES occ
                          ON ds.RESIDENT_ID = occ.RESIDENT_ID
                          AND ds.DEFICIT_ID = occ.DEFICIT_ID
                          AND occ.OCCURRENCE_DATE >= DATEADD(day, ?, CURRENT_DATE())
                      WHERE ds.DEFICIT_ID = ?
                      AND ds.DEFICIT_STATUS = ''ACTIVE''
                      GROUP BY ds.RESIDENT_ID
                      HAVING COUNT(occ.OCCURRENCE_ID) < ?`,
            binds: [-lb, def.deficit_id, def.threshold]
        });
        var checkResult = checkStmt.execute();

        while (checkResult.next()) {
            var resId = checkResult.getColumnValue("RESIDENT_ID");
            residentsAffected.add(resId);

            var deactStmt = snowflake.createStatement({
                sqlText: `UPDATE DRI_DEFICIT_STATUS
                          SET DEFICIT_STATUS = ''EXPIRED'', LOAD_TIMESTAMP = CURRENT_TIMESTAMP()
                          WHERE RESIDENT_ID = ? AND DEFICIT_ID = ?`,
                binds: [resId, def.deficit_id]
            });
            deactStmt.execute();
            indicatorsExpired++;
        }
    }

    details.push({step: "threshold_reevaluation", deficits_checked: thresholdDeficits.length, additional_expired: indicatorsExpired});

    // STEP 3: Clear expired rejections
    var clearRejStmt = snowflake.createStatement({
        sqlText: `UPDATE DRI_CLINICAL_DECISIONS
                  SET STATUS = ''EXPIRED''
                  WHERE STATUS = ''ACTIVE''
                  AND DECISION_TYPE = ''REJECTED''
                  AND EXPIRY_DATE IS NOT NULL
                  AND EXPIRY_DATE < CURRENT_DATE()`
    });
    clearRejStmt.execute();
    var rejCleared = clearRejStmt.getNumRowsAffected();

    details.push({step: "clear_expired_rejections", count: rejCleared});

    // STEP 4: Recalculate DRI scores for affected residents
    var affectedArray = Array.from(residentsAffected);
    if (affectedArray.length > 0) {
        for (var j = 0; j < affectedArray.length; j++) {
            var scoreStmt = snowflake.createStatement({
                sqlText: `MERGE INTO DRI_DEFICIT_SUMMARY t
                          USING (
                              SELECT ? as RESIDENT_ID,
                                     COUNT(*) / 32.0 as DRI_SCORE
                              FROM DRI_DEFICIT_STATUS
                              WHERE RESIDENT_ID = ? AND DEFICIT_STATUS = ''ACTIVE''
                          ) s
                          ON t.RESIDENT_ID = s.RESIDENT_ID
                          WHEN MATCHED THEN UPDATE SET
                              DRI_SCORE = s.DRI_SCORE,
                              LOAD_TIMESTAMP = CURRENT_TIMESTAMP(),
                              SEVERITY_BAND = CASE
                                  WHEN s.DRI_SCORE <= 0.2 THEN ''Low''
                                  WHEN s.DRI_SCORE <= 0.4 THEN ''Medium''
                                  WHEN s.DRI_SCORE <= 0.6 THEN ''High''
                                  ELSE ''Very High''
                              END
                          WHEN NOT MATCHED THEN INSERT (RESIDENT_ID, DRI_SCORE, SEVERITY_BAND, LOAD_TIMESTAMP)
                          VALUES (?, s.DRI_SCORE,
                                  CASE
                                      WHEN s.DRI_SCORE <= 0.2 THEN ''Low''
                                      WHEN s.DRI_SCORE <= 0.4 THEN ''Medium''
                                      WHEN s.DRI_SCORE <= 0.6 THEN ''High''
                                      ELSE ''Very High''
                                  END,
                                  CURRENT_TIMESTAMP())`,
                binds: [affectedArray[j], affectedArray[j], affectedArray[j]]
            });
            scoreStmt.execute();
        }
    }

    details.push({step: "recalculate_scores", residents_updated: affectedArray.length});

} catch (err) {
    var endTime = new Date();
    var durationMs = endTime - startTime;

    var errorResult = {
        run_id: vRunId,
        status: "FAILED",
        error: err.message,
        details: details
    };

    var logErrorRun = snowflake.createStatement({
        sqlText: `INSERT INTO DRI_PROCESSOR_RUNS
                  (RUN_ID, RUN_TYPE, CLIENT_SYSTEM_KEY, TRIGGERED_BY,
                   INDICATORS_EXPIRED, RUN_DURATION_MS, RUN_STATUS, ERROR_MESSAGE, DETAILS_JSON)
                  VALUES (?, ''TIME'', ?, ?, ?, ?, ''FAILED'', ?, PARSE_JSON(?))`,
        binds: [vRunId, P_CLIENT_SYSTEM_KEY, P_TRIGGERED_BY, indicatorsExpired, durationMs, err.message, JSON.stringify(errorResult)]
    });
    logErrorRun.execute();

    return errorResult;
}

var endTime = new Date();
var durationMs = endTime - startTime;

var result = {
    run_id: vRunId,
    status: "SUCCESS",
    indicators_expired: indicatorsExpired,
    indicators_renewed: indicatorsRenewed,
    residents_affected: residentsAffected.size,
    duration_ms: durationMs,
    details: details
};

// Log the processor run
var logRun = snowflake.createStatement({
    sqlText: `INSERT INTO DRI_PROCESSOR_RUNS
              (RUN_ID, RUN_TYPE, CLIENT_SYSTEM_KEY, TRIGGERED_BY,
               INDICATORS_EXPIRED, INDICATORS_RENEWED, RESIDENTS_AFFECTED,
               RUN_DURATION_MS, RUN_STATUS, DETAILS_JSON)
              VALUES (?, ''TIME'', ?, ?, ?, ?, ?, ?, ''SUCCESS'', PARSE_JSON(?))`,
    binds: [vRunId, P_CLIENT_SYSTEM_KEY, P_TRIGGERED_BY, indicatorsExpired, indicatorsRenewed, residentsAffected.size, durationMs, JSON.stringify(result)]
});
logRun.execute();

return result;
';

-- =============================================================================
-- 3. DRI_EVENT_PROCESSOR
-- =============================================================================
-- Processes indicator confirmations and rejections from review queue

CREATE OR REPLACE PROCEDURE DRI_EVENT_PROCESSOR(
    P_RESIDENT_ID FLOAT,
    P_CLIENT_SYSTEM_KEY VARCHAR,
    P_DEFICIT_ID VARCHAR,
    P_DEFICIT_NAME VARCHAR,
    P_APPROVAL_TYPE VARCHAR,
    P_APPROVED_BY VARCHAR,
    P_EVIDENCE_TEXT VARCHAR,
    P_SOURCE_ID VARCHAR,
    P_SOURCE_TABLE VARCHAR,
    P_ANALYSIS_ID VARCHAR,
    P_QUEUE_ID VARCHAR,
    P_SUPPRESSION_DAYS FLOAT DEFAULT 90
)
RETURNS VARIANT
LANGUAGE JAVASCRIPT
EXECUTE AS CALLER
AS '
var runId = snowflake.createStatement({sqlText: "SELECT UUID_STRING() as ID"}).execute();
runId.next();
var vRunId = runId.getColumnValue("ID");

var startTime = new Date();

// Get rule details
var ruleStmt = snowflake.createStatement({
    sqlText: "SELECT DEFICIT_TYPE, COALESCE(EXPIRY_DAYS, 0) as EXPIRY_DAYS, " +
             "CASE WHEN LOOKBACK_DAYS_HISTORIC = ''all'' OR LOOKBACK_DAYS_HISTORIC IS NULL THEN 9999 " +
             "ELSE TRY_TO_NUMBER(LOOKBACK_DAYS_HISTORIC) END as LOOKBACK_DAYS, " +
             "COALESCE(RENEWAL_REMINDER_DAYS, 7) as RENEWAL_REMINDER_DAYS, " +
             "COALESCE(RULES_JSON[0]:threshold::NUMBER, 1) as THRESHOLD " +
             "FROM DRI_RULES " +
             "WHERE DEFICIT_ID = ? AND IS_CURRENT_VERSION = TRUE",
    binds: [P_DEFICIT_ID]
});
var ruleResult = ruleStmt.execute();

var deficitType = "UNKNOWN";
var expiryDays = 0;
var lookbackDays = 365;
var renewalReminderDays = 7;
var threshold = 1;

if (ruleResult.next()) {
    deficitType = ruleResult.getColumnValue("DEFICIT_TYPE") || "UNKNOWN";
    expiryDays = ruleResult.getColumnValue("EXPIRY_DAYS") || 0;
    lookbackDays = ruleResult.getColumnValue("LOOKBACK_DAYS") || 365;
    renewalReminderDays = ruleResult.getColumnValue("RENEWAL_REMINDER_DAYS") || 7;
    threshold = ruleResult.getColumnValue("THRESHOLD") || 1;
}

var indicatorActivated = false;
var occurrenceCount = 0;
var expiryDate = null;
var message = "";

var suppressionDays = (P_SUPPRESSION_DAYS !== null && P_SUPPRESSION_DAYS !== undefined) ? P_SUPPRESSION_DAYS : 90;

if (P_APPROVAL_TYPE === "CONFIRMED") {
    // Log the occurrence
    var occId = snowflake.createStatement({sqlText: "SELECT UUID_STRING() as ID"}).execute();
    occId.next();
    var vOccId = occId.getColumnValue("ID");

    var insertOcc = snowflake.createStatement({
        sqlText: "INSERT INTO DRI_INDICATOR_OCCURRENCES " +
                 "(OCCURRENCE_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, DEFICIT_ID, DEFICIT_NAME, " +
                 "OCCURRENCE_DATE, SOURCE_ID, SOURCE_TABLE, EVIDENCE_TEXT, " +
                 "APPROVED_BY, APPROVAL_DATE, ANALYSIS_ID, QUEUE_ID) " +
                 "VALUES (?, ?, ?, ?, ?, CURRENT_DATE(), ?, ?, ?, ?, CURRENT_TIMESTAMP(), ?, ?)",
        binds: [vOccId, P_RESIDENT_ID, P_CLIENT_SYSTEM_KEY || "", P_DEFICIT_ID, P_DEFICIT_NAME || "",
                P_SOURCE_ID || "", P_SOURCE_TABLE || "", P_EVIDENCE_TEXT || "", P_APPROVED_BY, P_ANALYSIS_ID || "", P_QUEUE_ID || ""]
    });
    insertOcc.execute();

    // Count occurrences in lookback window
    var countStmt = snowflake.createStatement({
        sqlText: "SELECT COUNT(*) as CNT FROM DRI_INDICATOR_OCCURRENCES " +
                 "WHERE RESIDENT_ID = ? AND DEFICIT_ID = ? " +
                 "AND OCCURRENCE_DATE >= DATEADD(day, ?, CURRENT_DATE())",
        binds: [P_RESIDENT_ID, P_DEFICIT_ID, -lookbackDays]
    });
    var countResult = countStmt.execute();
    countResult.next();
    occurrenceCount = countResult.getColumnValue("CNT");

    // Check if threshold is met
    if (occurrenceCount >= threshold) {
        indicatorActivated = true;

        var expiryDateStr = null;
        if (deficitType === "PERSISTENT" || expiryDays === 0) {
            expiryDate = null;
            expiryDateStr = null;
        } else {
            var expStmt = snowflake.createStatement({
                sqlText: "SELECT TO_VARCHAR(DATEADD(day, ?, CURRENT_DATE()), ''YYYY-MM-DD'') as EXP",
                binds: [expiryDays]
            });
            var expResult = expStmt.execute();
            expResult.next();
            expiryDateStr = expResult.getColumnValue("EXP");
            expiryDate = expiryDateStr;
        }

        // Upsert DRI_DEFICIT_STATUS
        var statusSql = "MERGE INTO DRI_DEFICIT_STATUS t " +
                  "USING (SELECT ? as RESIDENT_ID, ? as DEFICIT_ID) s " +
                  "ON t.RESIDENT_ID = s.RESIDENT_ID AND t.DEFICIT_ID = s.DEFICIT_ID " +
                  "WHEN MATCHED THEN UPDATE SET " +
                  "DEFICIT_STATUS = ''ACTIVE'', " +
                  "DEFICIT_START_DATE = CURRENT_DATE(), " +
                  "DEFICIT_EXPIRY_DATE = " + (expiryDateStr ? "''" + expiryDateStr + "''" : "NULL") + ", " +
                  "DEFICIT_LAST_OCCURRENCE = CURRENT_DATE(), " +
                  "LOAD_TIMESTAMP = CURRENT_TIMESTAMP() " +
                  "WHEN NOT MATCHED THEN INSERT ( " +
                  "RESIDENT_ID, LOAD_TIMESTAMP, DEFICIT_ID, DEFICIT_STATUS, DEFICIT_START_DATE, DEFICIT_EXPIRY_DATE, DEFICIT_LAST_OCCURRENCE " +
                  ") VALUES (?, CURRENT_TIMESTAMP(), ?, ''ACTIVE'', CURRENT_DATE(), " + (expiryDateStr ? "''" + expiryDateStr + "''" : "NULL") + ", CURRENT_DATE())";
        var mergeStatus = snowflake.createStatement({
            sqlText: statusSql,
            binds: [P_RESIDENT_ID, P_DEFICIT_ID, P_RESIDENT_ID, P_DEFICIT_ID]
        });
        mergeStatus.execute();

        // Upsert DRI_CLINICAL_DECISIONS
        var decId = snowflake.createStatement({sqlText: "SELECT UUID_STRING() as ID"}).execute();
        decId.next();
        var vDecId = decId.getColumnValue("ID");

        var decisionSql = "MERGE INTO DRI_CLINICAL_DECISIONS t " +
                  "USING (SELECT ? as RESIDENT_ID, ? as DEFICIT_ID) s " +
                  "ON t.RESIDENT_ID = s.RESIDENT_ID AND t.DEFICIT_ID = s.DEFICIT_ID AND t.STATUS = ''ACTIVE'' " +
                  "WHEN MATCHED THEN UPDATE SET " +
                  "DECISION_TYPE = ''CONFIRMED'', " +
                  "DECISION_DATE = CURRENT_TIMESTAMP(), " +
                  "DECIDED_BY = ?, " +
                  "EXPIRY_DATE = " + (expiryDateStr ? "''" + expiryDateStr + "''" : "NULL") + " " +
                  "WHEN NOT MATCHED THEN INSERT ( " +
                  "DECISION_ID, RESIDENT_ID, DEFICIT_ID, DEFICIT_NAME, DECISION_TYPE, " +
                  "DEFICIT_TYPE, EXPIRY_DATE, DEFAULT_EXPIRY_DAYS, RENEWAL_REMINDER_DAYS, STATUS, DECISION_DATE, DECIDED_BY " +
                  ") VALUES (?, ?, ?, ?, ''CONFIRMED'', ?, " + (expiryDateStr ? "''" + expiryDateStr + "''" : "NULL") + ", ?, ?, ''ACTIVE'', CURRENT_TIMESTAMP(), ?)";
        var mergeDecision = snowflake.createStatement({
            sqlText: decisionSql,
            binds: [P_RESIDENT_ID, P_DEFICIT_ID, P_APPROVED_BY,
                    vDecId, P_RESIDENT_ID, P_DEFICIT_ID, P_DEFICIT_NAME || "", deficitType, expiryDays, renewalReminderDays, P_APPROVED_BY]
        });
        mergeDecision.execute();

        message = "Indicator activated (" + occurrenceCount + " of " + threshold + " occurrences)";
    } else {
        message = "Occurrence logged (" + occurrenceCount + " of " + threshold + " needed)";
    }

} else if (P_APPROVAL_TYPE === "REJECTED") {
    var suppressionExpiryStr = null;
    if (suppressionDays > 0) {
        var suppStmt = snowflake.createStatement({
            sqlText: "SELECT TO_VARCHAR(DATEADD(day, ?, CURRENT_DATE()), ''YYYY-MM-DD'') as EXP",
            binds: [suppressionDays]
        });
        var suppResult = suppStmt.execute();
        suppResult.next();
        suppressionExpiryStr = suppResult.getColumnValue("EXP");
    }

    var rejDecId = snowflake.createStatement({sqlText: "SELECT UUID_STRING() as ID"}).execute();
    rejDecId.next();
    var vRejDecId = rejDecId.getColumnValue("ID");

    var rejSql = "MERGE INTO DRI_CLINICAL_DECISIONS t " +
              "USING (SELECT ? as RESIDENT_ID, ? as DEFICIT_ID) s " +
              "ON t.RESIDENT_ID = s.RESIDENT_ID AND t.DEFICIT_ID = s.DEFICIT_ID AND t.STATUS = ''ACTIVE'' " +
              "WHEN MATCHED THEN UPDATE SET " +
              "DECISION_TYPE = ''REJECTED'', " +
              "EXPIRY_DATE = " + (suppressionExpiryStr ? "''" + suppressionExpiryStr + "''" : "NULL") + ", " +
              "DECISION_DATE = CURRENT_TIMESTAMP(), " +
              "DECIDED_BY = ?, " +
              "DECISION_REASON = ? " +
              "WHEN NOT MATCHED THEN INSERT ( " +
              "DECISION_ID, RESIDENT_ID, DEFICIT_ID, DEFICIT_NAME, DECISION_TYPE, " +
              "DEFICIT_TYPE, EXPIRY_DATE, STATUS, DECISION_DATE, DECIDED_BY, DECISION_REASON " +
              ") VALUES (?, ?, ?, ?, ''REJECTED'', ?, " + (suppressionExpiryStr ? "''" + suppressionExpiryStr + "''" : "NULL") + ", ''ACTIVE'', CURRENT_TIMESTAMP(), ?, ?)";
    var mergeRej = snowflake.createStatement({
        sqlText: rejSql,
        binds: [P_RESIDENT_ID, P_DEFICIT_ID, P_APPROVED_BY, P_EVIDENCE_TEXT || "",
                vRejDecId, P_RESIDENT_ID, P_DEFICIT_ID, P_DEFICIT_NAME || "", deficitType, P_APPROVED_BY, P_EVIDENCE_TEXT || ""]
    });
    mergeRej.execute();

    var mergeRejStatus = snowflake.createStatement({
        sqlText: "MERGE INTO DRI_DEFICIT_STATUS t " +
                 "USING (SELECT ? as RESIDENT_ID, ? as DEFICIT_ID) s " +
                 "ON t.RESIDENT_ID = s.RESIDENT_ID AND t.DEFICIT_ID = s.DEFICIT_ID " +
                 "WHEN MATCHED THEN UPDATE SET " +
                 "DEFICIT_STATUS = ''REJECTED'', " +
                 "LOAD_TIMESTAMP = CURRENT_TIMESTAMP() " +
                 "WHEN NOT MATCHED THEN INSERT ( " +
                 "RESIDENT_ID, LOAD_TIMESTAMP, DEFICIT_ID, DEFICIT_STATUS, DEFICIT_START_DATE " +
                 ") VALUES (?, CURRENT_TIMESTAMP(), ?, ''REJECTED'', CURRENT_DATE())",
        binds: [P_RESIDENT_ID, P_DEFICIT_ID, P_RESIDENT_ID, P_DEFICIT_ID]
    });
    mergeRejStatus.execute();

    if (suppressionDays > 0) {
        message = "Indicator rejected, suppressed for " + suppressionDays + " days";
    } else {
        message = "Indicator rejected (not suppressed)";
    }
}

var endTime = new Date();
var durationMs = endTime - startTime;

var result = {
    run_id: vRunId,
    resident_id: P_RESIDENT_ID,
    deficit_id: P_DEFICIT_ID,
    approval_type: P_APPROVAL_TYPE,
    deficit_type: deficitType,
    threshold: threshold,
    occurrences_in_window: occurrenceCount,
    indicator_activated: indicatorActivated,
    expiry_date: expiryDate,
    suppression_days: suppressionDays,
    message: message
};

// Log the processor run
var resultJson = JSON.stringify(result).replace(/''/g, "''''");
var logSql = "INSERT INTO DRI_PROCESSOR_RUNS " +
             "(RUN_ID, RUN_TYPE, CLIENT_SYSTEM_KEY, TRIGGERED_BY, RESIDENT_ID, " +
             "INDICATORS_ACTIVATED, OCCURRENCES_LOGGED, RUN_DURATION_MS, RUN_STATUS, DETAILS_JSON) " +
             "SELECT ?, ''EVENT'', ?, ''APPROVAL'', ?, ?, ?, ?, ''SUCCESS'', PARSE_JSON(''" + resultJson + "'')";
var logRun = snowflake.createStatement({
    sqlText: logSql,
    binds: [vRunId, P_CLIENT_SYSTEM_KEY || "", P_RESIDENT_ID, indicatorActivated ? 1 : 0, 1, durationMs]
});
logRun.execute();

// Update the queue item status
if (P_QUEUE_ID) {
    var updateQueue = snowflake.createStatement({
        sqlText: "UPDATE DRI_REVIEW_QUEUE " +
                 "SET STATUS = ''REVIEWED'', " +
                 "REVIEWED_BY = ?, " +
                 "REVIEWED_AT = CURRENT_TIMESTAMP() " +
                 "WHERE QUEUE_ID = ?",
        binds: [P_APPROVED_BY, P_QUEUE_ID]
    });
    try {
        updateQueue.execute();
    } catch (e) {
        // Queue update is not critical
    }
}

return result;
';

-- =============================================================================
-- VERIFICATION
-- =============================================================================
SELECT 'Stored procedures created successfully!' AS STATUS;

SHOW PROCEDURES LIKE 'DRI%';
SHOW PROCEDURES LIKE 'CALCULATE_DRI%';
