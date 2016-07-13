"""Hashmal style."""

def hashmal_style():
    return hashmal_style_sheet

hashmal_style_sheet = """

QStatusBar[hasError=true], QLineEdit[hasError=true],
QLabel[hasError=true], QTextEdit[hasError=true], QPlainTextEdit[hasError=true] {
  background: rgba(255, 0, 0, 25%);
}

QLineEdit[hasSuccess=true], QCheckBox[hasSuccess=true] {
  background: rgba(0, 255, 0, 25%);
}

ScriptCompilationLog {
  background: rgba(250, 250, 110, 75%);
}
"""
