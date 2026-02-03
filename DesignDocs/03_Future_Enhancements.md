1. The Streamlit app has several pages that are TBC / placeholders.  They need to have their designs finalised then be built
2. Snowflake offers an evaluation capability.  See details below: 

Snowflake has a new feature https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability when you look at the design documents in this folder /Users/sweingartner/CoCo/AgedCare/DesignDocs and perhaps the code as well, can you explain to me whether integrating this capability would be beneficial, how so, and would it be fairly easy to do? 

Let me read the design documents and check the memory for project context:

Let me also look at the core LLM analysis code to understand how Cortex is currently being used:

dri_analysis.py

Now I have a complete picture. Let me provide you with a comprehensive analysis:

AI Observability Integration Analysis
Would it be beneficial?
Yes, highly beneficial. Based on your design documents and code, integrating AI Observability would directly address several explicit requirements and add significant value:

Your Current Need	How AI Observability Helps
<1% false positive target (from ~10%)	Systematic evaluations with groundedness and context relevance scores would quantify prompt/model improvements
Prompt engineering UI (page 2)	Built-in comparison feature compares prompts/models side-by-side with quality metrics
Traceability requirement (Section 2.8)	Tracing captures every step: input prompts → retrieved RAG context → LLM inference → output
Human review workflow	Evaluation metrics can pre-filter low-confidence items, reducing reviewer workload
Model testing (Claude vs Regex comparison)	Automated LLM-as-judge scoring eliminates manual FP validation
Audit trail (DRI_LLM_ANALYSIS, DRI_AUDIT_LOG)	Traces stored in event tables provide richer audit data than raw JSON
Specific metrics that would help your use case:

Groundedness score: Detects if Claude's indicator detections are grounded in the actual resident notes (catches hallucinations)
Context relevance: Measures if RAG-retrieved indicator definitions are relevant to the query
Answer relevance: Validates the JSON response addresses the 33 indicators appropriately
How easy would integration be?
Moderate effort - requires changes but not architectural rewrites:

What's Compatible Now
Your DRI_LLM_ANALYSIS table already stores raw LLM responses ✓
You're using Cortex Complete (SNOWFLAKE.CORTEX.COMPLETE) ✓
You have batch processing with BATCH_RUN_ID tracking ✓
Required Changes
Python Environment (external to Snowflake currently):

Modify dri_analysis.py to wrap calls with TruLens instrumentation:

Create EXTERNAL AGENT in Snowflake:

Environment variable:

Key Limitation
"You can't run your project in a Snowflake Notebook"

Your app runs on SPCS (Streamlit container), so you'd need to either:

Run evaluations from the SPCS container (should work)
Run batch evaluations from a local Python environment connecting to Snowflake
Effort Estimate
Task	Effort
Install TruLens packages in SPCS container	1-2 hours
Create EXTERNAL AGENT + permissions	1 hour
Instrument dri_analysis.py	2-4 hours
Create evaluation datasets (ground truth)	4-8 hours
Build evaluation dashboard in Streamlit	4-8 hours
Total	~2-3 days
Recommendation
Integrate it - the payoff for your <1% FP target is significant. You're already manually validating FP rates (Section 10.4 in Technical Design shows TEST_FP_VALIDATION table). AI Observability automates this with LLM-as-judge scoring, giving you continuous quality metrics instead of point-in-time manual reviews.