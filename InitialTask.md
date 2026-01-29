I am a sales engineer at Snowflake.   Your initial task is to produce a design document md file or files but don't start coding yet.  Here is the task.   

My customer is Telstra Health who builds and runs aged care facility systems.  About 60,000 aged care patients are managed by this system.  In this system, there are a lot of medical notes.   

A new project per the design /Users/sweingartner/CoCo/AgedCare/Reference/medical_transcripts_solution_analysis.md is designed to look at those notes and to determine what is the new DRI.   The document defines what the DRI is and also at the bottom defines the specific calculation that must be followed.  


The project team has ingested all of the data from the aged care system into Snowflake into about 10 different tables and dynamic views.   Then a notebook uses regex and rules and fuzzy search to find records that need a review to increase the DRI score.  a calculation looks at those scores.   All the code and sample data for this project that was built based off the design document can be found in the /Users/sweingartner/CoCo/AgedCare/Confidential folder.  


The problem is that that the solution that was built is finding about 10% of records to be false positives.  For example, if the note says "the patient's son has asthma" then the regex flags that as a patient who has asthma needing review as it found the keyword asthma.  Telstra Health has stated the quality of the scoring is so bad it risks their position in the market.  We must improve the quality.  When you look at the code, you will see it is REGEX and rules.  We want to switch this to a smarter LLM with a good prompt and the right data fed into it.  


Snowflake is now able to use Claude 4.5 in Australia.  So, the plan I have is that we will have a business facing prompt engineering screen where the business can continually alter a prompt of what they are looking for.  THe key task is to identify events / indicators and load into target tables the records that a human must look at.  Currently about 10% of records are marked they must be looked at which is way to high when we scale out to 1 million records.  We want about 1% false positives rather than 10%.  

I think a solution  might be a RAG to look up the key informtation contained in the requirements document.  This would be held in a table in a snowflake table of what indicators to tag and how to calculate a DRI.   

A key part of the solution is a good prompt that is fed into the LLM and I want you to help create the intial prompt.  The users should have a UI where they are able to continually alter and improve the prompt.  The output should be a JSON which can be used programatically.    

 Claude can makes an smarter, context driven decision as to whether the DRI needs to change.   The output is a few tables for structured data and then PowerBI and an API back into the app are the interface where aged care facility workers can see key info and decide whether they want to adjust the DRI level.  Additionally the output would be json with text which could show informatoin back in a flexible manner similar to the streamlit app I discuss below.  

I'd like the new solution to properly tag indicators, calculate a new DRI, explain why it did so, give a confidence score and and give evidence as to why.  It should also link back to key records for traceability / explainability.  So this would makes it easy and fast for for the aged care facility worker to approve the change. 

I have demoed the medical notes demo to Telstra Health and discussed it and they see it as a great solution to their existing problem.  I want to rework the medical notes demo (designed to demo to medical doctors and health authorities around GP visits) and adapt the solution to focus on the aged care facility industry.    All of the code and all of the design documents for the medical notes demo is in this folder /Users/sweingartner/CoCo/AgedCare/Reference.  

Can you ask me 5 to 10 or so important questions as to how I would like the solution redesigned and then I want you to produce some new design documents.   I would like to start with a funcational design.  After I approve that then you can build the detailed designs and begin coding.  

The idea is that the existing notebook will be replaced with a new solution heavily inspired by this medical notes demo.    The solution will have key elements.   
1) Snowflake Cortex - Claude 4.5 is used rather than regex.  
2). users should be prsented a streamlit SPCS ui similar to /Users/sweingartner/CoCo/AgedCare/Reference/src/pages/3_🔬_Prompt_and_Model_Testing.py.  what that allows is aged care business matter experts to be able to continually play with the prompt to continually increase the accuracy and to look for new things.   After they fine tune a prompt, it can be tested and productionised by IT to run regurlarly in a pipeline (the medical notes demo doesn't show how to productoinise a new prompt but for now we can design for that.  Maybe the prompt in a UDF function or snowflake notebook is altered accordinly.).   There would only be a few users of that page, they would be trained medical professionals who know what they are looking for with DRI and other similar aged care requirements 
3) There are several business reporting dashboard streamlit pages in the demo "population health analysis, cost analysis, medicaiton safety, quality metrics"  I'd like you to have as a placeholder that these will be redesigned after we fix the rest of the solution

However, that is my initial design as to resolve the busienss requirements and I am open to changing any of that.  