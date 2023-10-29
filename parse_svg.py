import xml.etree.ElementTree as ET
SCALE = 10
FLIP_Y = False

tree = ET.parse('logga.svg')
root = tree.getroot()
out_root = ET.Element('map', xmlns="http://openorienteering.org/apps/mapper/xml/v2", version="9")
# georeferencing = ET.SubElement(root, 'georeferencing', scale="10000")
# projected_crs = ET.SubElement(georeferencing, 'projected_crs', id="Local")
barrier = ET.SubElement(out_root, 'barrier', version="6", required="0.6.0")


colors = ET.SubElement(barrier, 'colors')
symbols = ET.SubElement(barrier, 'symbols', id="ISOM 2017-2")

# Create a function to add a symbol element
def add_symbol(id, fill_color):

    h = fill_color.lstrip('#')
    r, g, b = tuple(str(int(h[i:i+2], 16)/255) for i in (0, 2, 4))
    id = str(id)

    color = ET.SubElement(colors, 'color', priority=str(int(id)-1), name=f"SVG_{id}", c="0.35", m="0.85", y="0", k="0", opacity="1")
    ET.SubElement(color, 'rgb', method="custom", r=r, g=g, b=b)
    ET.SubElement(color, 'cmyk', method="rgb")
    symbol = ET.SubElement(symbols, 'symbol', type=str(4), id=id, code=id, name=f"SVG_{id}")
    ET.SubElement(symbol, 'description')
    ET.SubElement(symbol, 'area_symbol', inner_color=str(int(id)-1), min_area="1125", patterns="0")


parts = ET.SubElement(barrier, 'parts', count="1", current="0")
part = ET.SubElement(parts, 'part', name="default part")
objects = ET.SubElement(part, 'objects', count="1")
last_color = ""
last_symbol = 0
for path in reversed(root.findall('.//{http://www.w3.org/2000/svg}path')):
    # Process i reverse because we want to have the last elements at top and with lowest priority (=at the top) in mapper
    style = path.get('style')
    fill_color = None
    if not style:
        continue
    for style_attr in style.split(';'):
        if style_attr.startswith('fill:'):
            fill_color = style_attr.split(':')[-1]
            if fill_color == "none" or fill_color[:15] == "url(#linearGrad":
                continue
            if not fill_color == last_color:
                last_symbol+=1
                last_color = fill_color
                add_symbol(str(last_symbol), fill_color)
            # break

    d = path.get('d')
    coordinates = []
    d = d.split(" ")
    controll_points_left = 0
    last_node = [0, 0]

    start_point = [0, 0]
    is_rel_coord = True
    doing_bezier = False
    skip_next = False
    for i, item in enumerate(d):
        try:
            if skip_next:
                skip_next = False
                continue
            if item.isalpha():
                skip_next = True
                arg = item
                if item.lower() == "z" and i==len(d)-1:
                    continue
                if d[i+1].isalpha():
                    cord = d[i+2].split(",")
                    skip_next = False
                else:
                    cord = d[i+1].split(",")
                cord = [int(float(i)*SCALE) for i in cord]

                if arg.isupper():
                    # Absolute position
                    last_node = [0, 0]
                    is_rel_coord = False
                else:
                    if i == 0:
                        last_node = [0, 0]
                    else:
                        last_node = coordinates[-1]
                    is_rel_coord = True
                arg = arg.lower()

                if arg == "v":
                    last_node[0] = coordinates[-1][0]
                    coordinates.append([last_node[0], cord[0] + last_node[1]])

                elif arg == "h":
                    last_node[1] = coordinates[-1][1]
                    coordinates.append([last_node[0] + cord[0], last_node[1]])

                elif arg == "l":  # Line
                    # Cleanup of potential 1
                    coordinates[-1] = coordinates[-1][:2]
                    doing_bezier = False
                    coordinates.append([last_node[0] + cord[0], last_node[1] + cord[1]])

                elif arg == "c":  # Bezier line
                    controll_points_left = 2
                    doing_bezier = True
                    if len(coordinates[-1]) == 2:
                        coordinates[-1].append(1)
                    coordinates.append([last_node[0] + cord[0], last_node[1] + cord[1]])

                elif arg == "z":  # Close curve
                    # Cleanup of potential 1
                    coordinates[-1] = coordinates[-1][:2]
                    coordinates.append([start_point[0], start_point[1], 18])
                    start_point = [start_point[0] + cord[0], start_point[1] + cord[1]]

                elif arg == "m":  # Relative coordinates
                    doing_bezier = False
                    start_point = [last_node[0] + cord[0], last_node[1] + cord[1]]
                    coordinates.append(start_point)

                else:
                    print(d)

            else:
                cord = [int(float(i)*SCALE) for i in item.split(",")]
                if doing_bezier:
                    if controll_points_left == 0:
                        controll_points_left = 3
                        last_node = coordinates[-1]
                    controll_points_left -= 1
                else:
                    if is_rel_coord:
                        last_node = coordinates[-1]

                if not is_rel_coord:
                    # Absolute position
                    last_node = [0, 0]
                if controll_points_left==0 and doing_bezier:
                    coordinates.append([last_node[0] + cord[0], last_node[1] + cord[1], 1])
                else:
                    coordinates.append([last_node[0] + cord[0], last_node[1] + cord[1]])
        except:
            print(d)

    # Remove potential 1
    coordinates[-1] = coordinates[-1][:2]
    # Reverse y-component
    if FLIP_Y:
        coordinates = [[c[0], -c[1], c[2]]  if len(c)==3 else [c[0], -c[1]] for c in coordinates]

    str_coord =  ";".join([" ".join([str(i) for i in s]) for s in coordinates])
    obj = ET.Element('object', type="1", symbol=str(last_symbol))
    coords = ET.SubElement(obj, 'coords', count=str(len(coordinates)))
    if d[-1].lower() == "z":
        coords.text = str_coord + " 16;"
    else:
        coords.text = str_coord + " 18;"
    pattern = ET.SubElement(obj, 'pattern', rotation="0")
    coord = ET.SubElement(pattern, 'coord', x="0", y="0")
    objects.append(obj)

out_root = ET.ElementTree(out_root)
ET.indent(out_root, '  ')
out_root.write('output.omap', encoding="utf-8", xml_declaration=True)
