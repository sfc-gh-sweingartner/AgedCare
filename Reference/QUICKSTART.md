# Healthcare AI Demo - Quick Start Guide

Get the Healthcare AI Demo running in your Snowflake account in under 10 minutes!

## ⚡ Prerequisites

1. **Snowflake Account** with Cortex AI features enabled
2. **Python 3.11+** installed locally
3. **Git** for cloning the repository

## 🚀 5-Minute Setup

### Step 1: Clone and Install
```bash
git clone https://github.com/sfc-gh-sweingartner/MedicalTranscriptsSPCS.git
cd MedicalTranscriptsSPCS
# Using pip with pyproject.toml (recommended)
pip install -e .
# Or using uv (faster, modern Python package installer)
# uv pip install -e .
```

### Step 2: Configure Snowflake
Create `~/.snowflake/config.toml`:
```toml
default_connection_name = "healthcare_demo"

[connections.healthcare_demo]
account = "YOUR_ACCOUNT"
user = "YOUR_USERNAME"
password = "YOUR_PASSWORD"
role = "ACCOUNTADMIN"
warehouse = "YOUR_WAREHOUSE"
```

### Step 3: Deploy Everything
```bash
python scripts/deploy_healthcare_demo.py
```

### Step 4: Start the Demo
```bash
streamlit run src/streamlit_main.py
```

### Step 5: Open and Explore
Navigate to [http://localhost:8501](http://localhost:8501)

## 🎯 What Gets Deployed

- ✅ **PMC_PATIENTS Database** - 167K+ medical case studies
- ✅ **HEALTHCARE_DEMO Database** - All analysis tables and procedures
- ✅ **AI Processing Engine** - Batch processing with Cortex AI
- ✅ **Demo Scenarios** - Pre-configured presentation cases
- ✅ **Streamlit App** - 9 healthcare AI use case pages

## 📋 Demo Pages to Explore

1. **🏥 Data Foundation** - Explore the medical case dataset
2. **🩺 Clinical Decision Support** - AI-powered diagnosis tools  
3. **🔬 Prompt and Model Testing** - Test AI models in real-time
4. **📊 Population Health Analytics** - Analyze patient cohorts
5. **💰 Cost Analysis** - Predict healthcare costs
6. **💊 Medication Safety** - Drug interaction analysis
7. **📈 Quality Metrics** - Care quality assessment
8. **🤖 AI Model Performance** - Benchmark AI models
9. **📋 Demo Guide** - Presentation scenarios

## 🔧 Quick Troubleshooting

**Connection Issues?**
```bash
# Test your connection
python -c "from scripts.deploy_healthcare_demo import *; HealthcareDemoDeployment().get_connection()"
```

**Deployment Problems?**
```bash
# Validate deployment
python scripts/validate_deployment.py
```

**Streamlit Not Starting?**
```bash
# Check Python version (must be 3.11+)
python --version

# Reinstall dependencies
pip install -e . --upgrade
```

## ⚠️ Important Notes

- **Demo System Only** - Not for clinical use
- **Cortex AI Required** - Ensure it's enabled on your account  
- **Large Dataset** - PMC-Patients.csv is ~200MB
- **Processing Time** - Initial deployment takes 5-10 minutes

## 🆘 Need Help?

1. Check the complete [README.md](README.md) for detailed instructions
2. Run the validation script: `python scripts/validate_deployment.py`
3. Review Snowflake query history for error details

---

**🎉 That's it!** Your Healthcare AI Demo should be running at http://localhost:8501

Start with the **Clinical Decision Support** page for the best first impression!
