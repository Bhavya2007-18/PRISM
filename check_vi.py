import pathlib, textwrap

dst = pathlib.Path(r'd:/WORK AND STUDY/PRISM/frontend/src/components/VoiceInterface.jsx')

CONTENT = textwrap.dedent('''
import { useState, useRef, useEffect } from ''react''
PLACEHOLDER
''').strip()

dst.write_text(CONTENT, encoding='utf-8')
print('done', len(CONTENT))
