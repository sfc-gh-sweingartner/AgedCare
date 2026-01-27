# Streamlit Style Guide - Cursor AI Rules

## Overview
This comprehensive style guide provides three distinct approaches for building professional Streamlit applications. It combines proven design principles with practical implementation guidance for AI assistants to create consistently high-quality, enterprise-ready applications.

## Universal Design Principles

### Core Development Philosophy
1. **Progressive Enhancement**: Start with core functionality, add visual enhancements incrementally. Ensure the app works before making it beautiful.
2. **Minimal Cognitive Load**: Use strong information hierarchy with cards, sections, and clear summaries. Guide user attention deliberately.
3. **File Management**: Always prefer editing existing files over creating new ones. Move unused files to a TRASH/ folder rather than deleting. Avoid file proliferation.
4. **Security First**: Use single database/schema patterns. Avoid SQL scripts that reference other scripts - each should be self-contained and runnable standalone.
5. **Runtime Awareness**: Be conscious of deployment environment differences (Legacy Streamlit has package restrictions, SPCS has full PyPI access).
6. **Responsive Design**: Prefer built-in Streamlit components over brittle custom CSS. Use stable, semantic HTML structures.

### Layout and Structure Fundamentals
- **Stable Visual Structure**: Define layout containers at script start using `st.container()` and `st.empty()`. Fill content later to prevent shifting layouts.
- **Semantic Hierarchy**: Use `st.title()`, `st.header()`, `st.subheader()` consistently. Each page should have only one `st.title()`.
- **Strategic Whitespace**: Use whitespace as a design tool, not just empty space. Group related elements, separate unrelated ones.
- **Information Grouping**: Use `st.container(border=True)` or card components to visually group related information.

---

## Style Guide 1: Corporate Standard

**Philosophy**: Clean, professional, and highly stable aesthetic prioritizing clarity and reliability. Ideal for enterprise demos, financial reports, and conservative business environments.

### Implementation Rules
- **Page Layout**: Always use `st.set_page_config(layout="wide")` for professional appearance
- **Navigation**: Primary navigation in `st.sidebar` only. Use `st.tabs` for secondary, intra-page navigation
- **Content Organization**: All content sections must use `st.container(border=True)` to create visible, bordered cards
- **Layout Structure**: Use `st.columns()` within containers to align related elements horizontally
- **Component Restrictions**: Use ONLY native Streamlit components. No third-party UI libraries.
- **CSS Restrictions**: Minimal custom CSS allowed. Maximum: adjust main block-container padding only.

### Color Theme (config.toml)
```toml
[theme]
primaryColor = "#0062df"      # Corporate blue for interactive elements
backgroundColor = "#ffffff"    # Clean white background
secondaryBackgroundColor = "#f0f2f6"  # Light gray for sidebar/widgets
textColor = "#262730"         # Dark gray text
font = "sans serif"           # Professional sans-serif font
```

### Prompting Pattern
"Apply the **Corporate Standard** style guide to this Streamlit application:
- Use wide layout and native Streamlit components only
- All navigation in sidebar, content in bordered containers
- Follow the corporate color theme
- No third-party components or extensive CSS allowed"

---

## Style Guide 2: Modern Minimalist

**Philosophy**: Contemporary, elegant design with generous whitespace and curated third-party components. Creates premium, bespoke application feel. Ideal for executive summaries, product showcases, and tech-forward audiences.

### Implementation Rules
- **Page Layout**: Use `st.set_page_config(layout="wide")`
- **Navigation**: Horizontal menu at top using `streamlit-option-menu`. Sidebar for contextual filters only.
- **Content Organization**: Use `streamlit-shadcn-ui` card components. No aggressive borders - separation through shadows and spacing.
- **Required Libraries**: `streamlit-option-menu`, `streamlit-shadcn-ui`
- **Interactive Elements**: All buttons, inputs, and widgets should use `streamlit-shadcn-ui` components
- **CSS Requirements**: Apply targeted CSS for component spacing and styling (medium complexity)

### Color Theme (config.toml)
```toml
[theme]
primaryColor = "#5a5a5a"      # Muted, sophisticated gray
backgroundColor = "#fcfcfc"    # Off-white to reduce eye strain
secondaryBackgroundColor = "#f0f2f6"  # Light gray
textColor = "#31333f"         # Subtle dark text
font = "sans serif"
```

### Required CSS
```python
st.markdown("""
<style>
/* Add vertical space between cards */
div > div[data-testid^="stComponent"] {
    gap: 1.5rem;
}
/* Style the horizontal option menu */
.st-emotion-cache-10trblm {
    border-bottom: 1px solid #e6e6e6;
    padding-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)
```

### Prompting Pattern
"Apply the **Modern Minimalist** style guide to this Streamlit application:
- Use horizontal navigation with streamlit-option-menu
- All content in streamlit-shadcn-ui cards with generous spacing
- Apply the modern minimalist theme and required CSS
- Focus on clean aesthetics and premium feel"

---

## Style Guide 3: Data-Dense Powerhouse

**Philosophy**: Maximum information density and user control for expert users. Dashboard-style interface with draggable/resizable components. Ideal for operational dashboards, monitoring tools, and analyst workbenches.

### Implementation Rules
- **Theme**: Use dark theme with `base = "dark"` in config.toml
- **Layout Engine**: Core layout must use `streamlit-elements` draggable grid system
- **Navigation**: Compact `streamlit-option-menu` in sidebar or horizontal top bar
- **Metrics Display**: Prominent use of `st.metric()` for KPIs with custom styling
- **Required Libraries**: `streamlit-elements`, `streamlit-option-menu`
- **CSS Requirements**: Aggressive CSS to reduce padding/margins for maximum density (high complexity)

### Color Theme (config.toml)
```toml
[theme]
base = "dark"                 # Inherit dark theme base
primaryColor = "#1c83e1"      # Bright blue for visibility
backgroundColor = "#0e1117"    # Dark background reduces eye strain
secondaryBackgroundColor = "#262730"  # Dark gray containers
textColor = "#fafafa"         # High contrast white text
font = "sans serif"
```

### Required CSS
```python
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 0rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
.st-emotion-cache-z5fcl4 {
    padding-top: 2rem;
}
div[data-testid="stMetric"] {
    background-color: #262730;
    border-radius: 0.5rem;
    padding: 1rem;
}
</style>
""", unsafe_allow_html=True)
```

### Prompting Pattern
"Apply the **Data-Dense Powerhouse** style guide to this Streamlit application:
- Use dark theme and streamlit-elements draggable grid layout
- All components should be resizable dashboard items
- Maximize information density with custom CSS
- Focus on efficiency and expert user needs"

---

## Technical Best Practices

### Package Management
- **Environment Awareness**: Always identify deployment target first (Legacy Streamlit vs SPCS)
- **Legacy Streamlit in Snowflake**: Restrict to Python 3.11 and packages from `https://repo.anaconda.com/pkgs/snowflake/`
- **Streamlit SPCS**: Full PyPI access via uv, no Python version restrictions, can use latest packages
- **Version Pinning**: Always pin package versions in requirements.txt and pyproject.toml
- **SPCS Documentation**: Document uv package installations and any custom dependencies

### Component Ecosystem Guide
**Essential Components by Category:**

**Navigation & Layout:**
- `streamlit-option-menu`: Professional navigation menus
- `streamlit-elements`: Draggable dashboard grids
- `streamlit-shadcn-ui`: Modern UI component library

**Data Display:**
- `streamlit-aggrid`: Advanced data tables with sorting/filtering
- `streamlit-plotly-events`: Interactive chart event handling

**Visual Enhancement:**
- `streamlit-extras`: Utility components (badges, cards, spacing)
- `streamlit-lottie`: Loading animations

### CSS Customization Guidelines
1. **Stability First**: Use `key` parameter on widgets for stable CSS targeting
2. **Specificity**: Write specific CSS selectors to avoid unintended side effects
3. **Browser Tools**: Always use browser developer tools to identify correct CSS classes
4. **Future-Proofing**: Prefer styling approaches that are less likely to break with Streamlit updates

### Security and Database Patterns
- **Single Schema**: Keep all data in one database and one schema for simplicity
- **Standalone Scripts**: SQL scripts should never reference other scripts
- **Connection Management**: Use centralized connection helper patterns
- **Data Access**: Always validate and sanitize user inputs for database queries

---

## Multi-Project Application Patterns

### Project Integration
1. **Design Document**: Each project should specify which style guide to use in its design document
2. **Rules Application**: Add this rules file to project when style application is needed
3. **Consistent Prompting**: Use the specific prompting patterns provided for each style

### Style Selection Criteria
- **Corporate Standard**: Conservative enterprise clients, regulatory compliance, maximum stability
- **Modern Minimalist**: Executive presentations, product demos, contemporary feel required
- **Data-Dense Powerhouse**: Operations teams, analysts, monitoring dashboards, expert users

### Migration Between Styles
When changing styles:
1. **Backup First**: Move current implementation to TRASH/ folder
2. **Component Audit**: Check which third-party components need to be added/removed  
3. **Theme Update**: Update config.toml for new color scheme
4. **CSS Replacement**: Replace custom CSS with style-specific requirements
5. **Testing**: Verify all functionality works with new components

---

## Prompting Examples for Common Scenarios

### New Project Style Application
"I'm starting a new Streamlit project for [audience type]. Please apply the [Style Guide Name] style guide and create a professional application structure with the following pages: [list pages]."

### Existing Project Style Change
"Please convert this existing Streamlit application to use the [Style Guide Name] style guide. Preserve all functionality but update the UI, navigation, and visual design according to the style guide rules."

### Style Guide Compliance Check
"Please review this Streamlit application against the [Style Guide Name] rules and identify any inconsistencies or areas that need improvement."

### Component Recommendation
"I need to add [functionality] to my Streamlit app using the [Style Guide Name] style. What components and implementation approach should I use?"

---

*This style guide should be applied consistently across all Streamlit projects to ensure professional, maintainable, and user-friendly applications.*
