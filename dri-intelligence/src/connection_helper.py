import os
import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session

def get_snowflake_session():
    if "snowflake_session" in st.session_state:
        return st.session_state.snowflake_session
    
    try:
        try:
            session = get_active_session()
        except Exception:
            session = Session.builder.configs({
                "connection_name": os.getenv("SNOWFLAKE_CONNECTION_NAME", "DEMO_SWEINGARTNER")
            }).create()
        
        session.sql("USE DATABASE AGEDCARE").collect()
        session.sql("USE SCHEMA AGEDCARE").collect()
        
        st.session_state.snowflake_session = session
        return session
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        return None

def execute_query(query: str, session=None):
    if session is None:
        session = get_snowflake_session()
    if session is None:
        return None
    try:
        result = session.sql(query).collect()
        return result
    except Exception as e:
        st.error(f"Query error: {e}")
        return None

def execute_query_df(query: str, session=None):
    if session is None:
        session = get_snowflake_session()
    if session is None:
        return None
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        st.error(f"Query error: {e}")
        return None
