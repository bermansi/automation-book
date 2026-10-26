"""Run with: python3 -m unittest discover -s tests -v

Fixtures are generated locally using the existing dependencies. No private
course source or extra test package is needed.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from lxml import etree
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('semantic_builder', ROOT / 'scripts/build-from-word-semantic.py')
BUILDER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILDER
SPEC.loader.exec_module(BUILDER)
W = BUILDER.W
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def paragraph(text, style=None, level=None):
    p = etree.Element(f'{{{W}}}p')
    properties = etree.SubElement(p, f'{{{W}}}pPr')
    if style:
        etree.SubElement(properties, f'{{{W}}}pStyle').set(f'{{{W}}}val', style)
    if level is not None:
        num = etree.SubElement(properties, f'{{{W}}}numPr')
        etree.SubElement(num, f'{{{W}}}ilvl').set(f'{{{W}}}val', str(level))
        etree.SubElement(num, f'{{{W}}}numId').set(f'{{{W}}}val', '1')
    etree.SubElement(etree.SubElement(p, f'{{{W}}}r'), f'{{{W}}}t').text = text
    return p


def write_word(path, chapters, heading=True):
    document = etree.Element(f'{{{W}}}document', nsmap={'w': W, 'r': R})
    body = etree.SubElement(document, f'{{{W}}}body')
    for number in chapters:
        title = next(c['title'] for c in BUILDER.legacy.CHAPTERS if c['number'] == number)
        if heading:
            body.append(paragraph(f'פרק {number} {title}', 'Heading1'))
        if number in '123':
            body.append(paragraph('נושא לדוגמה', level=1))
            body.append(paragraph(f'{number}.1.8 שאלה לדוגמה'))
        elif number == '4':
            body.append(paragraph('4.1 נושא לדוגמה'))
            body.append(paragraph('8. שאלה לדוגמה'))
        else:
            body.append(paragraph('5.1 מבחן לדוגמה'))
            for part in range(4):
                body.append(paragraph('מהו הפתרון של סעיף זה בשאלה', level=0))
                body.append(paragraph('פתרון'))
                body.append(paragraph('זהו פתרון מפורט לסעיף בשאלה'))
            continue
        body.append(paragraph('זהו גוף השאלה המפורט לבדיקה'))
        body.append(paragraph('פתרון'))
        body.append(paragraph('זהו פתרון מפורט לבדיקה'))
    numbering = f'''<w:numbering xmlns:w="{W}"><w:abstractNum w:abstractNumId="0">'''
    for level in range(3):
        numbering += f'<w:lvl w:ilvl="{level}"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%{level+1}."/></w:lvl>'
    numbering += '</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('word/document.xml', etree.tostring(document))
        archive.writestr('word/numbering.xml', numbering)
        archive.writestr('word/styles.xml', f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>')
        archive.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>')
        archive.writestr('word/_rels/document.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        archive.writestr('_rels/.rels', f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>')


class MultiWordTests(unittest.TestCase):
    def test_time_limit_symbol_order_and_ltr_isolation(self):
        from bs4 import BeautifulSoup
        for source in ('∞ t→', '\uf0a5 t\uf0ae', '∞ → t', 't → ∞'):
            soup = BeautifulSoup(f'<p>מה ערך התהליך בזמן t=2, בזמן {source}</p>', 'html.parser')
            BUILDER.legacy.postprocess_soup(soup)
            self.assertEqual(soup.find_all(class_='ltr-inline')[-1].get_text(), 't→∞')
            self.assertEqual(soup.find_all(class_='ltr-inline')[-1]['dir'], 'ltr')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.sources = []
        for number in '12345':
            source = self.folder / f'chapter-{number}.docx'
            write_word(source, [number])
            self.sources.append(source)

    def test_inputs_and_mapping(self):
        resolved = BUILDER.resolve_sources([self.folder], [])
        self.assertEqual(resolved, list(zip('12345', self.sources)))
        explicit = [f'{n}={p}' for n, p in reversed(list(zip('12345', self.sources)))]
        self.assertEqual(BUILDER.resolve_sources([], explicit), resolved)
        self.assertEqual(BUILDER.resolve_sources(self.sources, []), resolved)
        with self.assertRaises(SystemExit):
            BUILDER.resolve_sources(self.sources[:4], [])
        with self.assertRaises(SystemExit):
            BUILDER.resolve_sources([], explicit[:-1])
        with self.assertRaises(SystemExit):
            BUILDER.resolve_sources([self.sources[0]] * 5, [])
        with self.assertRaises(SystemExit):
            BUILDER.resolve_sources([], explicit + [explicit[0]])
        self.sources[2].unlink()
        with self.assertRaises(SystemExit):
            BUILDER.resolve_sources([self.folder], [])

    def test_chapter_context_and_wrong_file(self):
        with self.assertRaises(SystemExit):
            BUILDER.prepare_chapter(self.sources[0], '2', self.folder / 'wrong.docx')
        source = self.folder / 'no heading.docx'
        write_word(source, ['3'], heading=False)
        original = source.read_bytes()
        prepared = BUILDER.prepare_chapter(source, '3', self.folder / 'prepared.docx')
        structure = BUILDER.semantic_structure(prepared, self.folder / 'marked.docx')
        self.assertEqual([c['number'] for c in structure.chapters], ['3'])
        self.assertEqual([q.id for q in structure.questions], ['3.1.8'])
        self.assertEqual(source.read_bytes(), original)

    def test_appended_controller_question_keeps_existing_numbers(self):
        source = self.sources[0]
        with zipfile.ZipFile(source) as archive:
            entries = {item.filename: archive.read(item.filename) for item in archive.infolist()}
        root = etree.fromstring(entries['word/document.xml'])
        body = root.find(f'{{{W}}}body')
        for child in list(body)[1:]:
            body.remove(child)
        for index in range(1, 7):
            body.append(paragraph('נושא לדוגמה', level=1))
            if index == 6:
                for question in range(1, 7):
                    body.append(paragraph(f'{question}) שאלה בבקרה'))
                    body.append(paragraph('גוף השאלה'))
                    body.append(paragraph('פתרון'))
                    body.append(paragraph('פתרון השאלה'))
        entries['word/document.xml'] = etree.tostring(root)
        with zipfile.ZipFile(source, 'w') as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
        structure = BUILDER.semantic_structure(source, self.folder / 'controller-marked.docx')
        self.assertEqual([q.id for q in structure.questions],
                         ['1.6.1א', '1.6.1ב', '1.6.2א', '1.6.2ב', '1.6.3', '1.6.4'])

    def test_explicit_chapter_four_numbers_and_current_titles(self):
        source = self.sources[3]
        with zipfile.ZipFile(source) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        root = etree.fromstring(entries['word/document.xml'])
        body = root.find(f'{{{W}}}body')
        body.clear()
        for item in [paragraph('פרק 4 חיישנים ומפעילים', 'Heading1'),
                     paragraph('4.1 מערכות מדידה וחיישנים'),
                     paragraph('4.1.12.מרחק נסיעה לפי ספירות אנקודר'),
                     paragraph('זהו גוף השאלה'), paragraph('פתרון'), paragraph('זהו הפתרון')]:
            body.append(item)
        entries['word/document.xml'] = etree.tostring(root)
        with zipfile.ZipFile(source, 'w') as archive:
            for name, value in entries.items():
                archive.writestr(name, value)
        structure = BUILDER.semantic_structure(source, self.folder / 'chapter4-marked.docx')
        self.assertEqual([q.id for q in structure.questions], ['4.1.12'])
        self.assertEqual(structure.questions[0].title, '')
        self.assertEqual(structure.sections[0].title, 'מערכות מדידה וחיישנים')

    def test_mixed_first_answer_label(self):
        result = BUILDER.normalize_explicit_solution_labels(
            '<ol class="word-list-hebrew"><li><p>תשובה ראשונה</p></li></ol>'
            '<p>ב. תשובה שנייה</p><p>ג. תשובה שלישית</p><p>ד. תשובה רביעית</p>',
            'hebrew', ['א', 'ב', 'ג', 'ד'], 'explicit')
        self.assertIn('א. תשובה ראשונה', result)
        self.assertNotIn('<ol', result)

    def test_state_space_matrix_and_vector_dimensions(self):
        from types import SimpleNamespace
        math_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
        mt = lambda name: f'{{{math_ns}}}{name}'
        p = paragraph('')
        equation = etree.SubElement(p, mt('oMath'))
        def run(parent, value):
            etree.SubElement(etree.SubElement(parent, mt('r')), mt('t')).text = value
        def array(values):
            delimiter = etree.SubElement(equation, mt('d'))
            props = etree.SubElement(delimiter, mt('dPr'))
            etree.SubElement(props, mt('begChr')).set(mt('val'), '[')
            etree.SubElement(props, mt('endChr')).set(mt('val'), ']')
            expression = etree.SubElement(delimiter, mt('e'))
            for value in values:
                run(expression, value)
                run(expression, ' ')
            return expression
        run(equation, 'A=')
        a = array(['0', '1', '-6', '-5'])
        run(equation, ', B=')
        b = array(['0', '4'])
        run(equation, ', C=')
        c = array(['1', '0'])
        BUILDER.restore_state_space_arrays(
            [SimpleNamespace(element=p)], [SimpleNamespace(section='1.4', paragraph_index=0)])
        for expression, dimensions in [(a, [2, 2]), (b, [1, 1]), (c, [2])]:
            matrix = expression.find(mt('m'))
            self.assertIsNotNone(matrix)
            self.assertEqual([len(row.findall(mt('e'))) for row in matrix.findall(mt('mr'))], dimensions)
        self.assertEqual(''.join(a.itertext()), '01-6-5')
        # A dotted y denotes a state derivative here, not an output row.
        derivative = etree.Element(mt('acc'))
        equation.insert(0, derivative)
        run(equation, 'y=')
        derivative_vector = array(['x2', '3-5x2-6x1'])
        BUILDER.restore_state_space_arrays(
            [SimpleNamespace(element=p)], [SimpleNamespace(section='1.4', paragraph_index=0)])
        # Existing matrices supply no new flattened square candidate; include
        # another A expression to establish the dimension in this fixture.
        run(equation, 'A=')
        array(['0', '1', '-6', '-5'])
        BUILDER.restore_state_space_arrays(
            [SimpleNamespace(element=p)], [SimpleNamespace(section='1.4', paragraph_index=0)])
        self.assertEqual([len(row) for row in derivative_vector.find(mt('m')).findall(mt('mr'))], [1, 1])

    def test_literal_question_parts_require_matching_word_answer_scheme(self):
        source = self.sources[2]
        with zipfile.ZipFile(source) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        root = etree.fromstring(entries['word/document.xml'])
        body = root.find(f'{{{W}}}body')
        body.clear()
        for item in [paragraph('פרק 3 עיבוד תמונה', 'Heading1'),
                     paragraph('נושא לדוגמה', level=1), paragraph('3.1.8'),
                     paragraph('זהו נוסח השאלה'), paragraph('א. סעיף ראשון בשאלה'),
                     paragraph('ב. סעיף שני בשאלה'), paragraph('פתרון'),
                     paragraph('תשובה ראשונה', level=0), paragraph('תשובה שנייה', level=0)]:
            body.append(item)
        entries['word/document.xml'] = etree.tostring(root)
        def save():
            with zipfile.ZipFile(source, 'w') as archive:
                for name, value in entries.items():
                    archive.writestr(name, value)
        save()
        with self.assertRaisesRegex(SystemExit, 'Word answer labels do not match'):
            BUILDER.semantic_structure(source, self.folder / 'invalid.docx')
        entries['word/numbering.xml'] = entries['word/numbering.xml'].replace(b'val="decimal"', b'val="hebrew1"')
        save()
        structure = BUILDER.semantic_structure(source, self.folder / 'valid.docx')
        self.assertEqual(structure.questions[0].part_labels, ['א', 'ב'])
        self.assertEqual(structure.questions[0].solution_part_layout, 'word-list')

    def test_media_namespacing(self):
        results = []
        for number in '12345':
            docs = self.folder / number
            (docs / 'media').mkdir(parents=True)
            Image.new('RGB', (40, 40), (int(number)*40, 0, 0)).save(docs / 'media/image1.png')
            data = {'chapters': [{'number': number}], 'notes': '',
                    'structure': {'discoveredQuestions': 1, 'publishedQuestions': 1, 'draftQuestions': []},
                    'exercises': [{'number': f'{number}.1.1', 'section': f'{number}.1',
                                   'questionHtml': '<img src="media/image1.png">',
                                   'parts': [{'solutionHtml': '<img src="media/image1.png">'}]}]}
            results.append((number, data, docs))
        out = self.folder / 'merged'
        merged = BUILDER.combine_chapter_data(results, out)
        for number, exercise in zip('12345', merged['exercises']):
            name = f'chapter-{number}-image1.png'
            self.assertIn(name, exercise['questionHtml'])
            self.assertIn(name, exercise['parts'][0]['solutionHtml'])
            self.assertEqual((out / 'media' / name).read_bytes(), (self.folder / number / 'media/image1.png').read_bytes())

    @unittest.skipUnless(shutil.which('pandoc') and (shutil.which('soffice') or shutil.which('libreoffice')), 'Pandoc and LibreOffice required')
    def test_real_conversion_matches_combined_and_includes_added_question(self):
        combined = self.folder / 'combined.docx'
        write_word(combined, '12345')
        outputs = []
        for name, sources in [('combined', [combined]), ('split', self.sources)]:
            out = self.folder / f'output-{name}'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-from-word-semantic.py'),
                                     *map(str, sources), '--out', str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            raw = (out / 'assets/book-data.js').read_text()
            outputs.append(json.loads(raw.removeprefix('window.BOOK_DATA = ').rstrip(';\n')))
        self.assertEqual(outputs[0]['exercises'], outputs[1]['exercises'])
        self.assertEqual(outputs[0]['chapters'], outputs[1]['chapters'])
        self.assertEqual(outputs[1]['structure']['publishedQuestions'], 5)
        self.assertIn('3.1.8', [e['number'] for e in outputs[1]['exercises']])


if __name__ == '__main__':
    unittest.main()
