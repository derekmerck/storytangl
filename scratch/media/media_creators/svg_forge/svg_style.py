import re
from bs4 import BeautifulSoup

class SvgStyle:
    def __init__(self, svg_string):
        self.soup = BeautifulSoup(svg_string, 'lxml')
        self.styling_dict = {}
        self.parse_styles()

    def parse_styles(self):
        """Parse styles from group labels."""
        for group in self.soup.find_all('g', {'id': re.compile('.*')}):
            label = group.get('id')
            styles = re.findall(r'{{(.+?)}}', label)
            if styles:
                self.styling_dict[group] = styles[0]
                group['id'] = re.sub(r'{{.+?}}', '', label).strip()

    def strip_styles(self):
        """Strip existing styles/classes from SVG elements."""
        for tag in self.soup(True):
            if 'style' in tag.attrs:
                del tag['style']
            if 'class' in tag.attrs:
                del tag['class']

    def apply_styles(self):
        """Apply parsed styles to their respective groups."""
        for group, style in self.styling_dict.items():
            for child in group.find_all():
                child['style'] = style

    def get_styled_svg(self):
        """Combine all methods to return styled SVG string."""
        self.strip_styles()
        self.apply_styles()
        return str(self.soup)

# Usage:
# svg_style = SvgStyle(svg_string)
# styled_svg_string = svg_style.get_styled_svg()
