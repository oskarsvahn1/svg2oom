import xml.etree.ElementTree as ET

SCALE = 100
FLIP_Y = False

tree = ET.parse('Polder_se_cmyk.svg')
root = tree.getroot()
PARENT_MAP = {c: p for p in root.iter() for c in p}
out_root = ET.Element('map', xmlns="http://openorienteering.org/apps/mapper/xml/v2", version="9")
# georeferencing = ET.SubElement(root, 'georeferencing', scale="10000")
# projected_crs = ET.SubElement(georeferencing, 'projected_crs', id="Local")
barrier = ET.SubElement(out_root, 'barrier', version="6", required="0.6.0")


colors = ET.SubElement(barrier, 'colors')
symbols = ET.SubElement(barrier, 'symbols', id="ISOM 2017-2")

def add_color(id, fill_color):
    h = fill_color.lstrip('#')
    r, g, b = tuple(str(int(h[i:i+2], 16)/255) for i in (0, 2, 4))
    id = str(id)
    color = ET.SubElement(colors, 'color', priority=str(int(id)-1), name=f"SVG_{id}", c="0.35", m="0.85", y="0", k="0", opacity="1")
    ET.SubElement(color, 'rgb', method="custom", r=r, g=g, b=b)
    ET.SubElement(color, 'cmyk', method="rgb")

def add_area_symbol(id):
    symbol = ET.SubElement(symbols, 'symbol', type=str(4), id=id, code=id, name=f"SVG_{id}")
    ET.SubElement(symbol, 'description')
    ET.SubElement(symbol, 'area_symbol', inner_color=str(int(id)-1), min_area="1125", patterns="0")

def add_line_symbol(id, width):
    symbol = ET.SubElement(symbols, 'symbol', type=str(2), id=id, code=id, name=f"SVG_{id}")
    ET.SubElement(symbol, 'description')
    ET.SubElement(symbol, 'line_symbol', color=str(int(id)-1), line_width=str(width), join_style="2", cap_style="1")

parts = ET.SubElement(barrier, 'parts', count="1", current="0")
part = ET.SubElement(parts, 'part', name="default part")
objects = ET.SubElement(part, 'objects', count="1")
last_fill_color = ""
last_style  = ""



def get_coords(d, n, start, is_rel_coord, last_node=[0,0]):
    cords = []
    for i in range(start, start+n):
        cord = d[i].split(",")
        cord = [float(j)*SCALE for j in cord]
        if is_rel_coord:
            cord = [last_node[0] + cord[0], last_node[1] + cord[1]]
        cords.append(cord)
    return cords

last_symbol = 0

for path in reversed(root.findall('.//{http://www.w3.org/2000/svg}path')):
    # Process i reverse because we want to have the last elements at top and with lowest priority (=at the top) in mapper
    style = path.get('style')
    if not style:
        style = PARENT_MAP[path].get("style")
    fill_color = None
    if not style:
        continue

    style = {i.split(":")[0]: i.split(":")[1] for i in style.split(";")}
    if style.get("stroke") and not style.get("stroke") == "none":
        stroke_color = style.get("stroke")
        stroke_width = style.get("stroke-width")
        if not style == last_style:
            last_symbol+=1
            last_style = style
            last_stroke_color = stroke_color
            add_color(str(last_symbol), stroke_color)
            add_line_symbol(str(last_symbol), int(float(stroke_width)*SCALE))

    elif style.get("fill") and not style.get("fill") == "none":
        fill_color = style.get("fill")
        if fill_color[:15] == "url(#linearGrad":
            # Skip gradients
            fill_color = last_style.get("fill")
        if not style == last_style:
            last_symbol+=1
            last_style = style
            add_color(str(last_symbol), fill_color)
            add_area_symbol(str(last_symbol))

    d = path.get('d')
    coordinates = []
    d = d.split(" ")
    controll_points_left = 0
    last_node = [0, 0]

    start_point = [0, 0]
    is_rel_coord = True
    doing_bezier = False
    skip_next = False
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

            if arg== "z":  # Close curve
                # Cleanup of potential 1
                coordinates[-1] = coordinates[-1][:2]
                coordinates.append([start_point[0], start_point[1], 18])

            i+=1
        else:

            cord = d[i].split(",")
            cord = [float(j)*SCALE for j in cord]
            if is_rel_coord and len(coordinates) > 0: 
                last_node = coordinates[-1][:2]
            else:
                last_node = [0, 0]

            if arg == "v":
                n=1
                last_node[0] = coordinates[-1][0]
                coordinates.append([last_node[0], cord[0] + last_node[1]])
                i+=1


            elif arg == "h":
                last_node[1] = coordinates[-1][1]
                coordinates.append([last_node[0] + cord[0], last_node[1]])
                i+=1

            elif arg == "l":  # Line
                # Cleanup of potential 1
                coordinates[-1] = coordinates[-1][:2]
                coordinates.append([last_node[0] + cord[0], last_node[1] + cord[1]])
                i+=1


            elif arg == "q":
                n=2
                cords = get_coords(d, n, i, is_rel_coord, last_node)

                C0 = coordinates[-1][:2]
                C1 = [a + 2/3*(b-a) for a, b in zip(C0, cords[0])]
                C2 = [c + 2/3*(b-c) for b, c in zip(cords[0], cords[1])]
                C3 = cords[1]
                if len(coordinates[-1]) == 2:
                    coordinates[-1].append(1)
                coordinates.append(C1)
                coordinates.append(C2)
                coordinates.append(C3)
                i+=n

            elif arg == "c":  # Bezier line
                n=3
                cords = get_coords(d, n, i, is_rel_coord, last_node)

                if len(coordinates[-1]) == 2:
                    coordinates[-1].append(1)
                coordinates.append(cords[0])
                coordinates.append(cords[1])
                coordinates.append(cords[2])
                i+=n


            elif arg == "a":
                def add_start(cord):
                    return [last_node[0]+cord[0]-r_x, last_node[1]+cord[1]]

                last_node[1] = coordinates[-1][1]
                cord = d[i].split(",")
                r_x, r_y = [float(j)*SCALE for j in cord]
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
                if len(coordinates)>0 and len(coordinates[-1]) < 3:
                    coordinates[-1].append(18)
                start_point = [last_node[0] + cord[0], last_node[1] + cord[1]]
                coordinates.append(start_point)
                arg = "l"
                i+=1
            
            else:
                print(d)
                i+=1
    i+=1

    def transform(coordinates, path):
        transform = path.get("transform")
        if transform[:9] == "translate":
            x, y = transform[10:-1].split(",")
            x = float(x)*SCALE
            y = float(y)*SCALE
            return [[C[0]+x, C[1]+y, C[2]]  if len(C)==3 else [C[0]+x, C[1]+y] for C in coordinates]
        
        elif transform[:6] == "matrix":
            a, b, c, d, e, f = map(float, transform[7:-1].split(","))
            # newX = a * oldX + c * oldY + e 
            # newY = b * oldX + d * oldY + f 
            return [[C[0]*a + C[1]*c+e*SCALE, C[0]*b + C[1]*d+f*SCALE, C[2]]  if len(C)==3 else [C[0]*a + C[1]*c+e*SCALE, C[0]*b + C[1]*d+f*SCALE] for C in coordinates]
        else:
            return coordinates

    if path.get("transform"):
        coordinates = transform(coordinates, path)

    elif PARENT_MAP[path].get("transform"):
        coordinates = transform(coordinates, PARENT_MAP[path])


    if FLIP_Y:
        # Reverse y-component, convert to int
        coordinates = [[int(c[0]), -int(c[1]), c[2]]  if len(c)==3 else [int(c[0]), -int(c[1])] for c in coordinates]
    else:
        coordinates = [[int(c[0]), int(c[1]), c[2]]  if len(c)==3 else [int(c[0]), int(c[1])] for c in coordinates]


    str_coord =  ";".join([" ".join([str(i) for i in s]) for s in coordinates])
    obj = ET.Element('object', type="1", symbol=str(last_symbol))
    coords = ET.SubElement(obj, 'coords', count=str(len(coordinates)))
    coords.text = str_coord+";"
    pattern = ET.SubElement(obj, 'pattern', rotation="0")
    coord = ET.SubElement(pattern, 'coord', x="0", y="0")
    objects.append(obj)

out_root = ET.ElementTree(out_root)
ET.indent(out_root, '  ')
out_root.write('output.omap', encoding="utf-8", xml_declaration=True)
