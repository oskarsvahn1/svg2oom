import xml.etree.ElementTree as ET
import argparse
import re

class SVGConverter:
    def __init__(self, filename, scale=100, flip_y=True, do_point_symbol=True):
        self.scale = scale
        self.flip_y = flip_y
        self.do_point_symbol = do_point_symbol
        self.max_x, self.min_x, self.max_y, self.min_y = None, None, None, None

        self.tree = ET.parse(filename)
        self.filename = filename
        self.root = self.tree.getroot()
        self.width = float(self.tree.getroot().attrib["width"][:-2])
        self.heigth = float(self.tree.getroot().attrib["height"][:-2])

        self.parent_map = {c: p for p in self.root.iter() for c in p}
        self.map = ET.Element('map', xmlns="http://openorienteering.org/apps/mapper/xml/v2", version="9")
        self.colors = ET.SubElement(self.map, 'colors')
        self.barrier = ET.SubElement(self.map, 'barrier', version="6", required="0.6.0")
        self.symbols = ET.SubElement(self.barrier, 'symbols', id="ISOM 2017-2")

        self.parts = ET.SubElement(self.barrier, 'parts', count="1", current="0")
        self.part = ET.SubElement(self.parts, 'part', name="default part")
        self.objects = ET.SubElement(self.part, 'objects', count="1")


        self.last_symbol = 0
        self.last_style = ""

        if self.do_point_symbol:
            self.create_point_symbol()

    def create_point_symbol(self):
        symbol = ET.SubElement(self.symbols, 'symbol', type="1", id="0", code="999", name=self.filename[:-4])
        self.point_symbol = ET.SubElement(symbol, 'point_symbol', inner_radius="250", inner_color="-1", outer_width="0", outer_color="-1", elements="30")

    def add_color(self, id, fill_color):
        if fill_color=="#000":
            r, g, b = 0, 0, 0
        else:
            h = fill_color.lstrip('#')            
            r, g, b = tuple(str(int(h[i:i+2], 16)/255) for i in (0, 2, 4))
        id = str(id)
        color = ET.SubElement(self.colors, 'color', priority=str(int(id)-1), name=f"SVG_{id}", c="0.35", m="0.85", y="0", k="0", opacity="1")
        ET.SubElement(color, 'rgb', method="custom", r=r, g=g, b=b)
        ET.SubElement(color, 'cmyk', method="rgb")

    def add_area_symbol(self, id):
        symbol = ET.SubElement(self.symbols, 'symbol', type=str(4), id=id, code=id, name=f"SVG_{id}")
        ET.SubElement(symbol, 'description')
        ET.SubElement(symbol, 'area_symbol', inner_color=str(int(id)-1), min_area="1125", patterns="0")

    def add_line_symbol(self, id, width):
        symbol = ET.SubElement(self.symbols, 'symbol', type=str(2), id=id, code=id, name=f"SVG_{id}")
        ET.SubElement(symbol, 'description')
        ET.SubElement(symbol, 'line_symbol', color=str(int(id)-1), line_width=str(width), join_style="2", cap_style="1")

    def add_coords2obj(self, obj, coordinates):
        coords = ET.SubElement(obj, 'coords', count=str(len(coordinates)))
        coords.text = ";".join([" ".join([str(i) for i in s]) for s in coordinates]) + ";"
        pattern = ET.SubElement(obj, 'pattern', rotation="0")
        coord = ET.SubElement(pattern, 'coord', x="0", y="0")

    def add_element(self, symbol_color_nb, coordinates, stroke_width):
        element = ET.SubElement(self.point_symbol, 'element')
        if stroke_width:
            symbol = ET.SubElement(element, 'symbol', type="2", code="")
            line_symbol = ET.SubElement(symbol, 'line_symbol', color=symbol_color_nb, line_width=str(int(float(stroke_width)*self.scale)), join_style="2", cap_style="1")
        else:
            symbol = ET.SubElement(element, 'symbol', type="4", code="")
            area_symbol = ET.SubElement(symbol, 'area_symbol', inner_color=symbol_color_nb, min_area="0", patterns="0")

        obj = ET.SubElement(element, 'object', type="1")
        self.add_coords2obj(obj, coordinates)

    def get_coords(self, d, n, start, is_rel_coord, last_node):
        cords = []
        for i in range(start, start+n):
            cord = d[i].split(",")
            cord = [float(j)*self.scale for j in cord]
            if is_rel_coord:
                cord = [last_node[0] + cord[0], last_node[1] + cord[1]]
            cords.append(cord)
        return cords

    def transform(self, coordinates, path):
        transform = path.get("transform")
        if transform[:9] == "translate":
            x, y = transform[10:-1].split(",")
            x = float(x)*self.scale
            y = float(y)*self.scale
            return [[C[0]+x, C[1]+y, C[2]]  if len(C)==3 else [C[0]+x, C[1]+y] for C in coordinates]
        
        elif transform[:6] == "matrix":
            a, b, c, d, e, f = map(float, transform[7:-1].split(","))
            # newX = a * oldX + c * oldY + e 
            # newY = b * oldX + d * oldY + f 
            # Works only on point symbols
            if self.symbols[-1][-1] and self.symbols[-1][-1][-1][0][0].tag == 'line_symbol':
                self.symbols[-1][-1][-1][0][0].set("line_width", str(int(a * float(self.symbols[-1][-1][-1][0][0].attrib["line_width"]))))
            return [[C[0]*a + C[1]*c+e*self.scale, C[0]*b + C[1]*d+f*self.scale, C[2]]  if len(C)==3 else [C[0]*a + C[1]*c+e*self.scale, C[0]*b + C[1]*d+f*self.scale] for C in coordinates]
        elif transform[:5] == "scale":
            s = float(transform[6:-1])
            if self.symbols[-1][-1] and self.symbols[-1][-1][-1][0][0].tag == 'line_symbol':
                self.symbols[-1][-1][-1][0][0].set("line_width", str(int(s * float(self.symbols[-1][-1][-1][0][0].attrib["line_width"]))))

            return [[C[0]*s, C[1]*s, C[2]]  if len(C)==3 else [C[0]*s, C[1]*s] for C in coordinates]

        else:
            return coordinates

    def process_path(self, path):
        style = path.get('style')
        if not style:
            style = self.parent_map[path].get("style")
        if not style:
            style = self.parent_map[path].attrib

        fill_color = None
        if not style:
            return

        stroke_width = 0
        if type(style)==str:
            style = {i.split(":")[0]: i.split(":")[1] for i in style.split(";")}
        if style.get("stroke") and not style.get("stroke") == "none":
            stroke_color = style.get("stroke")
            stroke_width = style.get("stroke-width")
            if stroke_width[-2:]=="px":
                stroke_width = stroke_width[:1]
            if not style == self.last_style:
                self.last_symbol += 1
                self.last_style = style
                self.add_color(str(self.last_symbol), stroke_color)
                if not self.do_point_symbol:
                    self.add_line_symbol(str(self.last_symbol), int(float(stroke_width) * self.scale))
        elif style.get("fill") and not style.get("fill") == "none":
            fill_color = style.get("fill")
            if fill_color[:15] == "url(#linearGrad":
                # Skip gradients
                fill_color = self.last_style.get("fill")
            if not style == self.last_style:
                self.last_symbol += 1
                self.last_style = style
                self.add_color(str(self.last_symbol), fill_color)
                if not self.do_point_symbol:
                    self.add_area_symbol(str(self.last_symbol))

        d = path.get('d').strip()

        # split m1, m-1, 1m -> m 1, m -1, 1 m
        d = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', d)
        d = re.sub(r'([a-zA-Z])(-\d)', r'\1 \2', d)
        d = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', d)

        # d = re.sub(r'([a-zA-Z]+)(\d+)(-?)(\d*)', r'\1 \2\3\4', d)

        #split 1-2 -> 1 -2
        d = re.sub(r'(\d)(-)', r'\1 \2', d)
        # d = re.sub(r'(\s+)', lambda m: ',' if m.start() % 2 == 1 else ' ', d)

        # if space and comma is interchanged
        # d = re.sub(r'(\d\s\d)', 'ä', d)
        # d = re.sub(r',', ' ', d)
        # d = re.sub(r'ä', ',', d)

        coordinates = []
        d = d.split(" ")
        last_node = [0, 0]
        start_point = [0, 0]
        is_rel_coord = True
        arg = "m"
        i = 0
        while i < len(d):
            item = d[i]
            if item.isalpha():
                arg = item.lower()
                if item.isupper():
                    is_rel_coord = False
                else:
                    is_rel_coord = True

                if arg == "z":  # Close curve
                    # Cleanup of potential 1
                    coordinates[-1] = coordinates[-1][:2]
                    coordinates.append([start_point[0], start_point[1], 18])
                i += 1
            else:
                cord = d[i].split(",")
                cord = [float(j) * self.scale for j in cord]
                if is_rel_coord and coordinates:
                    last_node = coordinates[-1][:2]
                else:
                    last_node = [0, 0]

                if arg == "v":
                    n = 1
                    last_node[0] = coordinates[-1][0]
                    coordinates.append([last_node[0], cord[0] + last_node[1]])
                    i += 1
                elif arg == "h":
                    last_node[1] = coordinates[-1][1]
                    coordinates.append([last_node[0] + cord[0], last_node[1]])
                    i += 1
                elif arg == "l":  # Line
                    # Cleanup of potential 1
                    coordinates[-1] = coordinates[-1][:2]
                    coordinates.append([last_node[0] + cord[0], last_node[1] + cord[1]])
                    i += 1
                elif arg == "q":
                    n = 2
                    cords = self.get_coords(d, n, i, is_rel_coord, last_node)
                    C0 = coordinates[-1][:2]
                    C1 = [a + 2/3*(b-a) for a, b in zip(C0, cords[0])]
                    C2 = [c + 2/3*(b-c) for b, c in zip(cords[0], cords[1])]
                    C3 = cords[1]
                    if len(coordinates[-1]) == 2:
                        coordinates[-1].append(1)
                    coordinates.append(C1)
                    coordinates.append(C2)
                    coordinates.append(C3)
                    i += n
                elif arg == "c":  # Bezier line
                    n = 3
                    cords = self.get_coords(d, n, i, is_rel_coord, last_node)
                    if len(coordinates[-1]) == 2:
                        coordinates[-1].append(1)
                    coordinates.append(cords[0])
                    coordinates.append(cords[1])
                    coordinates.append(cords[2])
                    i += n
                elif arg == "a":
                    def add_start(cord):
                        return [last_node[0]+cord[0]-r_x, last_node[1]+cord[1]]

                    last_node[1] = coordinates[-1][1]
                    cord = d[i].split(",")
                    r_x, r_y = [float(j)*self.scale for j in cord]
                    # https://pomax.github.io/bezierinfo/#circles_cubic
                    k=0.551784777779014
                    
                    q1 = [r_x, 0]
                    q2 = [r_x,  r_y*k]
                    q3 = [k*r_x, r_y]
                    q4 = [0, r_y]
                    q5 = [-k*r_x, r_y]
                    q6 = [-r_x, k*r_y]
                    q7 = [-r_x, 0]
                    q8 = [-r_x, -k*r_y]
                    q9 = [-k*r_x, -r_y]
                    q10 = [0, -r_y]
                    q11 = [k*r_x, -r_y]
                    q12 = [r_x, -k*r_y]

                    # coordinates.append(add_start(q1))
                    coordinates[-1] = add_start(q1)
                    start_point = add_start(q1)
                    coordinates[-1].append(1)
                    coordinates.append(add_start(q2))
                    coordinates.append(add_start(q3))
                    coordinates.append(add_start(q4))
                    coordinates[-1].append(1)
                    coordinates.append(add_start(q5))
                    coordinates.append(add_start(q6))
                    coordinates.append(add_start(q7))
                    coordinates[-1].append(1)
                    coordinates.append(add_start(q8))
                    coordinates.append(add_start(q9))
                    coordinates.append(add_start(q10))
                    coordinates[-1].append(1)
                    coordinates.append(add_start(q11))
                    coordinates.append(add_start(q12))
                    arg = "a"
                    i+=20 #?

                elif arg == "m":  # Relative coordinates
                    if coordinates and len(coordinates[-1]) < 3:
                        coordinates[-1].append(18)
                    start_point = [last_node[0] + cord[0], last_node[1] + cord[1]]
                    coordinates.append(start_point)
                    arg = "l"
                    i += 1
                else:
                    print(d)
                    i += 1
        i += 1


        if path.get("transform"):
            coordinates = self.transform(coordinates, path)

        elif self.parent_map[path].get("transform"):
            coordinates = self.transform(coordinates, self.parent_map[path])
        elif self.parent_map[self.parent_map[path]].get("transform"):
            coordinates = self.transform(coordinates, self.parent_map[self.parent_map[path]])
        elif self.parent_map[self.parent_map[self.parent_map[path]]].get("transform"):
            coordinates = self.transform(coordinates, self.parent_map[self.parent_map[self.parent_map[path]]])
        # elif self.parent_map[self.parent_map[self.parent_map[self.parent_map[path]]]].get("transform"):
        #     coordinates = self.transform(coordinates, self.parent_map[self.parent_map[self.parent_map[self.parent_map[path]]]])
        # if self.parent_map[self.parent_map[self.parent_map[self.parent_map[self.parent_map[path]]]]].get("transform"):
        #     coordinates = self.transform(coordinates, self.parent_map[self.parent_map[self.parent_map[self.parent_map[self.parent_map[path]]]]])


        if self.flip_y:
            # Reverse y-component, convert to int
            coordinates = [[int(c[0]), -int(c[1]), c[2]] if len(c) == 3 else [int(c[0]), -int(c[1])] for c in coordinates]
        else:
            coordinates = [[int(c[0]), int(c[1]), c[2]] if len(c) == 3 else [int(c[0]), int(c[1])] for c in coordinates]

        if self.do_point_symbol:
            if not self.max_x:
                self.min_x = min([x[0] for x in coordinates])
                self.min_y = min([x[1] for x in coordinates])
                self.max_x = max([x[0] for x in coordinates])
                self.max_y = max([x[1] for x in coordinates])
            else:
                self.min_x = min(self.min_x, min([x[0] for x in coordinates]))
                self.min_y = min(self.min_y, min([x[1] for x in coordinates]))
                self.max_x = max(self.max_x, max([x[0] for x in coordinates]))
                self.max_y = max(self.max_y, max([x[1] for x in coordinates]))

            coordinates = [[C[0]-int(self.scale*self.width/2), C[1]-int(self.scale*self.heigth/2), C[2]]  if len(C)==3 else [C[0]-int(self.scale*self.width/2), C[1]-int(self.scale*self.heigth/2)] for C in coordinates]
            self.add_element(str(self.last_symbol - 1), coordinates, stroke_width)

        else:
            obj = ET.Element('object', type="1", symbol=str(self.last_symbol))
            self.add_coords2obj(obj, coordinates)
            self.objects.append(obj)




    def process_svg(self):
        for path in reversed(self.root.findall('.//{http://www.w3.org/2000/svg}path')):
            self.process_path(path)

    def save_output(self, filename):
        out_root = ET.ElementTree(self.map)
        ET.indent(out_root, '  ')
        if not filename:
            filename = self.filename[:-4]+".omap"
        print(f"Saving to {filename}")
        out_root.write(filename, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert SVG to OMap format.')
    parser.add_argument('filename', type=str, help='Input SVG file')
    parser.add_argument('outfile', type=str, nargs='?', default=None, help='Output OMAP file')
    parser.add_argument('--scale', type=int, default=100, help='Scaling factor (default: 100)')
    parser.add_argument('--flip_y', action='store_true', help='Flip Y-coordinate')
    parser.add_argument('--as_point', action='store_true', help='Output path as single point symbol')
    args = parser.parse_args()

    converter = SVGConverter(args.filename, scale=args.scale, flip_y=args.flip_y, do_point_symbol=args.as_point)
    converter.process_svg()
    converter.save_output(args.outfile)
