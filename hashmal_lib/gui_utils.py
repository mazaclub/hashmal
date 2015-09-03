from PyQt4.QtGui import QFont, QHBoxLayout

monospace_font = QFont('Monospace')
monospace_font.setStyleHint(QFont.TypeWriter)

script_file_filter = 'Coinscripts (*.coinscript);;Text files (*.txt);;All files (*.*)'

def floated_buttons(btns, left=False):
    """Returns a HBoxLayout with buttons floated to the right or left."""
    hbox = QHBoxLayout()
    for b in btns:
        hbox.addWidget(b)
    if left:
        hbox.addStretch(1)
    else:
        hbox.insertStretch(0, 1)
    return hbox

hashmal_style = '''

QStatusBar[hasError=true], QLineEdit[hasError=true] {
  background: rgba(255, 0, 0, 25%);
}
'''
