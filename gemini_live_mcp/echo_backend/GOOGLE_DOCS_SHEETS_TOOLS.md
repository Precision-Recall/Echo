# Google Docs & Sheets Creator Tools

## 🎯 Overview

Two new powerful tools have been added to create Google Docs and Google Sheets with **proper native formatting** using the Google Docs API and Google Sheets API.

## ✨ New Tools

### 1. `create_google_doc` - Google Docs Creator

Creates a professionally formatted Google Doc with:
- **Document title** (in TITLE style at the top)
- **Headings** (H1, H2, H3 with proper font sizes and spacing)
- **Text formatting** (bold, italic)
- **Lists** (bulleted and numbered)
- **Proper spacing** (paragraph spacing, line spacing)
- **Native Google Docs formatting** (not Markdown!)

#### Example Usage

**User Request:**
> "Create a 1-page document about Machine Learning"

**AI Response:**
1. Generates comprehensive content about ML
2. Structures it with proper formatting markers:
   ```
   # Introduction
   
   Machine learning is a subset of artificial intelligence...
   
   ## Key Concepts
   
   - Supervised learning
   - Unsupervised learning
   - Reinforcement learning
   
   ## Applications
   
   1. Image recognition
   2. Natural language processing
   3. Predictive analytics
   ```
3. Calls `create_google_doc(title="Introduction to Machine Learning", content=...)`
4. Returns a clickable Google Docs link

#### Formatting Syntax

The AI uses these markers (which are parsed and converted to native Google Docs formatting):

| Marker | Google Docs Style | Example |
|--------|-------------------|---------|
| `# Text` | HEADING_1 (20pt, bold) | `# Introduction` |
| `## Text` | HEADING_2 (16pt, bold) | `## Key Concepts` |
| `### Text` | HEADING_3 (14pt, bold) | `### Subsection` |
| `**text**` | Bold text | `**important**` → **important** |
| `*text*` | Italic text | `*emphasis*` → *emphasis* |
| `- Item` | Bullet list | `- First item` |
| `1. Item` | Numbered list | `1. First step` |
| Blank line | Paragraph spacing | (8pt spacing) |

#### API Details

**Function Signature:**
```python
async def create_google_doc(
    title: str,
    content: str,
    user_email: Optional[str] = None,
    firebase_token: Optional[str] = None
)
```

**Parameters:**
- `title` - Document title (appears at top in TITLE style)
- `content` - Structured text with formatting markers
- `user_email` - User's email (for OAuth token retrieval from Firebase)
- `firebase_token` - Firebase ID token (for authentication)

**Returns:**
```json
{
  "success": true,
  "document_id": "abc123...",
  "title": "Introduction to Machine Learning",
  "url": "https://docs.google.com/document/d/abc123.../edit",
  "message": "Successfully created Google Doc: Introduction to Machine Learning"
}
```

**Required Scopes:**
- `https://www.googleapis.com/auth/documents`

---

### 2. `create_google_sheet` - Google Sheets Creator

Creates a Google Sheet with optional headers and data.

#### Example Usage

**User Request:**
> "Create a spreadsheet to track student grades"

**AI Response:**
1. Determines appropriate structure
2. Calls:
   ```python
   create_google_sheet(
       title="Student Grades Tracker",
       headers=["Student Name", "Email", "Assignment 1", "Assignment 2", "Final Score"],
       data=[
           ["John Doe", "john@example.com", "95", "87", "91"],
           ["Jane Smith", "jane@example.com", "88", "92", "90"]
       ]
   )
   ```
3. Returns a clickable Google Sheets link

#### API Details

**Function Signature:**
```python
async def create_google_sheet(
    title: str,
    headers: Optional[List[str]] = None,
    data: Optional[List[List[str]]] = None,
    user_email: Optional[str] = None,
    firebase_token: Optional[str] = None
)
```

**Parameters:**
- `title` - Spreadsheet title
- `headers` - Optional list of column headers (e.g., `["Name", "Email", "Score"]`)
- `data` - Optional 2D list of data rows (e.g., `[["John", "john@ex.com", "95"], ...]`)
- `user_email` - User's email (for OAuth token retrieval from Firebase)
- `firebase_token` - Firebase ID token (for authentication)

**Returns:**
```json
{
  "success": true,
  "spreadsheet_id": "xyz789...",
  "title": "Student Grades Tracker",
  "url": "https://docs.google.com/spreadsheets/d/xyz789.../edit",
  "message": "Successfully created Google Sheet: Student Grades Tracker"
}
```

**Required Scopes:**
- `https://www.googleapis.com/auth/spreadsheets`

---

## 🔐 Authentication

Both tools use the **same OAuth tokens** already stored in Firebase for the user. No additional authentication needed!

### Token Flow:
1. User authorizes Google Classroom (which includes Docs & Sheets scopes)
2. Tokens stored in Firebase Firestore
3. Backend retrieves tokens when creating docs/sheets
4. Documents are created in the user's Google Drive

### Required Scopes (Already Included):
✅ `https://www.googleapis.com/auth/documents` - Create and edit Google Docs  
✅ `https://www.googleapis.com/auth/spreadsheets` - Create and edit Google Sheets

---

## 🎨 Why Native Formatting?

### ❌ What We DON'T Do:
- Insert Markdown text (e.g., `# Title` stays as literal text)
- Use plain text without structure
- Rely on users to manually format

### ✅ What We DO:
- Parse formatting markers
- Apply **native Google Docs styles**:
  - `TITLE` style (28pt, bold, top of document)
  - `HEADING_1` style (20pt, bold, 20pt top spacing)
  - `HEADING_2` style (16pt, bold, 16pt top spacing)
  - `HEADING_3` style (14pt, bold, 12pt top spacing)
  - `NORMAL_TEXT` style (11pt, 1.15 line spacing)
- Create **proper bullet/numbered lists** with Google Docs list formatting
- Apply **text styling** (bold, italic) inline

---

## 📝 Example: Complete Document Creation

### User Request:
> "Create a document explaining neural networks"

### AI Process:

1. **Generate Content:**
   ```
   # Neural Networks
   
   Neural networks are computing systems inspired by biological neural networks.
   
   ## Architecture
   
   A neural network consists of:
   
   - **Input layer**: Receives data
   - **Hidden layers**: Process information
   - **Output layer**: Produces results
   
   ## Types
   
   ### Feedforward Networks
   
   The simplest type where connections flow in one direction.
   
   ### Recurrent Networks
   
   Networks with feedback connections for *sequential* data.
   
   ## Applications
   
   1. Image classification
   2. Speech recognition
   3. Language translation
   ```

2. **Call Tool:**
   ```python
   create_google_doc(
       title="Neural Networks Explained",
       content=content_above
   )
   ```

3. **Result:**
   A beautifully formatted Google Doc with:
   - Large bold title at top: **Neural Networks Explained**
   - Main heading: **Neural Networks** (20pt)
   - Subheading: **Architecture** (16pt)
   - Bullet list with bold "Input layer", "Hidden layers", "Output layer"
   - Sub-subheading: **Feedforward Networks** (14pt)
   - Italic emphasis on "sequential"
   - Numbered list with proper formatting

---

## 🔧 Implementation Details

### Google Docs API - BatchUpdate Requests

The `_parse_and_format_content()` helper function converts formatted text into Google Docs API requests:

```python
requests = [
    # Insert text
    {'insertText': {'location': {'index': 1}, 'text': 'Hello'}},
    
    # Apply heading style
    {'updateParagraphStyle': {
        'range': {'startIndex': 1, 'endIndex': 6},
        'paragraphStyle': {'namedStyleType': 'HEADING_1'},
        'fields': 'namedStyleType'
    }},
    
    # Apply bold
    {'updateTextStyle': {
        'range': {'startIndex': 1, 'endIndex': 6},
        'textStyle': {'bold': True},
        'fields': 'bold'
    }},
    
    # Create bullet list
    {'createParagraphBullets': {
        'range': {'startIndex': 7, 'endIndex': 15},
        'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
    }}
]

docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
```

### Google Sheets API - Values Update

```python
sheets_service.spreadsheets().values().update(
    spreadsheetId=sheet_id,
    range='A1',
    valueInputOption='RAW',
    body={'values': [
        ['Name', 'Email', 'Score'],  # Headers
        ['John', 'john@ex.com', '95'],  # Data row 1
        ['Jane', 'jane@ex.com', '87']   # Data row 2
    ]}
).execute()
```

---

## 🧪 Testing

### Test Document Creation:
```bash
# In your chat interface, send:
"Create a 1-page document about Python programming"

# Expected: AI generates content and returns a Google Docs link
```

### Test Spreadsheet Creation:
```bash
# In your chat interface, send:
"Create a spreadsheet to track my expenses with categories"

# Expected: AI creates a sheet with appropriate headers (Date, Category, Amount, Description)
```

---

## 🚀 Benefits Over Apps Script

| Feature | Apps Script | Direct API (Our Approach) |
|---------|-------------|----------------------------|
| **Setup** | Create/deploy script project | ✅ No extra setup |
| **Performance** | Slower (execution overhead) | ✅ Fast (direct API calls) |
| **Authentication** | Separate auth flow | ✅ Uses existing OAuth tokens |
| **Debugging** | Harder (remote execution) | ✅ Easy (local debugging) |
| **Dependencies** | Manage script libraries | ✅ Python packages |
| **Formatting** | Manual DOM manipulation | ✅ Native API styles |

---

## 📚 References

- [Google Docs API - Documents](https://developers.google.com/docs/api/reference/rest/v1/documents)
- [Google Docs API - BatchUpdate](https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate)
- [Google Sheets API - Spreadsheets](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets)
- [Named Styles in Google Docs](https://developers.google.com/docs/api/concepts/structure#named_styles)

---

## ✅ Summary

- **Two new tools**: `create_google_doc` and `create_google_sheet`
- **Proper formatting**: Native Google Docs/Sheets styles (not Markdown)
- **Same authentication**: Uses existing OAuth tokens from Firebase
- **Easy to use**: AI generates content, tools handle formatting
- **Professional output**: Documents look like they were manually formatted in Google Docs

🎉 **Users can now ask the AI to create documents and spreadsheets, and get back shareable Google Drive links with beautifully formatted content!**

