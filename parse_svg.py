import xml.etree.ElementTree as ET
import argparse

class SVGConverter:
    def __init__(self, filename, scale=100, flip_y=True, do_point_symbol=True):
        self.scale = scale
        self.flip_y = flip_y
        self.do_point_symbol = do_point_symbol

        self.tree = ET.parse(filename)
        self.root = self.tree.getroot()
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
        symbol = ET.SubElement(self.symbols, 'symbol', type="1", id="0", code="999", name="SVG-logo")
        self.point_symbol = ET.SubElement(symbol, 'point_symbol', inner_radius="250", inner_color="-1", outer_width="0", outer_color="-1", elements="30")

    def add_color(self, id, fill_color):
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

    def get_coords(self, d, n, start, is_rel_coord, last_node):
        cords = []
        for i in range(start, start+n):
            cord = d[i].split(",")
            cord = [float(j)*self.scale for j in cord]
            if is_rel_coord:
                cord = [last_node[0] + cord[0], last_node[1] + cord[1]]
            cords.append(cord)
        return cords

    def add_element(self, symbol_color_nb, object_coordinates, stroke_width):
        element = ET.SubElement(self.point_symbol, 'element')

        if stroke_width:
            symbol = ET.SubElement(element, 'symbol', type="2", code="")
            line_symbol = ET.SubElement(symbol, 'line_symbol', color=symbol_color_nb, line_width=str(int(float(stroke_width)*self.scale)), join_style="2", cap_style="1")
        else:
            symbol = ET.SubElement(element, 'symbol', type="4", code="")
            area_symbol = ET.SubElement(symbol, 'area_symbol', inner_color=symbol_color_nb, min_area="0", patterns="0")

        obj = ET.SubElement(element, 'object', type="1")
        coords = ET.SubElement(obj, 'coords', count=str(len(object_coordinates)))
        coords.text = ";".join([" ".join([str(i) for i in s]) for s in object_coordinates]) + ";"
        pattern = ET.SubElement(obj, 'pattern', rotation="0")
        coord = ET.SubElement(pattern, 'coord', x="0", y="0")

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
            return [[C[0]*a + C[1]*c+e*self.scale, C[0]*b + C[1]*d+f*self.scale, C[2]]  if len(C)==3 else [C[0]*a + C[1]*c+e*self.scale, C[0]*b + C[1]*d+f*self.scale] for C in coordinates]
        else:
            return coordinates

    def process_path(self, path):
        style = path.get('style')
        if not style:
            style = self.parent_map[path].get("style")
        fill_color = None
        if not style:
            return

        stroke_width = 0
        style = {i.split(":")[0]: i.split(":")[1] for i in style.split(";")}
        if style.get("stroke") and not style.get("stroke") == "none":
            stroke_color = style.get("stroke")
            stroke_width = style.get("stroke-width")
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

        d = path.get('d')
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
                skip_next = True
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
                if is_rel_coord and len(coordinates) > 0:
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
                    # ... (unchanged)
                    i += 20  # ?
                elif arg == "m":  # Relative coordinates
                    if len(coordinates) > 0 and len(coordinates[-1]) < 3:
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

        if self.flip_y:
            # Reverse y-component, convert to int
            coordinates = [[int(c[0]), -int(c[1]), c[2]] if len(c) == 3 else [int(c[0]), -int(c[1])] for c in coordinates]
        else:
            coordinates = [[int(c[0]), int(c[1]), c[2]] if len(c) == 3 else [int(c[0]), int(c[1])] for c in coordinates]

        if self.do_point_symbol:
            self.add_element(str(self.last_symbol - 1), coordinates, stroke_width)
        else:
            str_coord = ";".join([" ".join([str(i) for i in s]) for s in coordinates])
            obj = ET.Element('object', type="1", symbol=str(self.last_symbol))
            coords = ET.SubElement(obj, 'coords', count=str(len(coordinates)))
            coords.text = str_coord + ";"
            pattern = ET.SubElement(obj, 'pattern', rotation="0")
            coord = ET.SubElement(pattern, 'coord', x="0", y="0")

            self.objects.append(obj)




    def process_svg(self):
        for path in reversed(self.root.findall('.//{http://www.w3.org/2000/svg}path')):
            self.process_path(path)

    def save_output(self, filename='output.omap'):
        out_root = ET.ElementTree(self.map)
        ET.indent(out_root, '  ')
        out_root.write(filename, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert SVG to OMap format.')
    parser.add_argument('filename', type=str, help='Input SVG file')
    parser.add_argument('--scale', type=int, default=100, help='Scaling factor (default: 100)')
    parser.add_argument('--flip_y', action='store_true', help='Flip Y-coordinate')
    parser.add_argument('--as_point', action='store_true', help='Disable point symbol')
    args = parser.parse_args()

    converter = SVGConverter(args.filename, scale=args.scale, flip_y=args.flip_y, do_point_symbol=args.as_point)
    converter.process_svg()
    converter.save_output()
