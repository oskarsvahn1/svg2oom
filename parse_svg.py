import xml.etree.ElementTree as ET

# Load the SVG file
tree = ET.parse('logga.svg')
root = tree.getroot()

# Define a dictionary to map symbol values
symbol_mapping = {
    '#000000': '1',
    # Add more mappings as needed
}
output_objects = ET.Element("objects")
output_colors = ET.Element("color")

parent_map = {c:p for p in tree.iter() for c in p}
# Iterate through path elements in the SVG
for path in root.findall('.//{http://www.w3.org/2000/svg}path'):
    style = path.get('style')

    # Extract fill color from the style attribute
    fill_color = None
    if not style:
        continue
    for style_attr in style.split(';'):
        if style_attr.startswith('fill:'):
            fill_color = style_attr.split(':')[-1]
            break

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
        if skip_next:
            skip_next =False
            continue
        if item.isalpha():
            skip_next = True
            arg = item
            if d[i+1].isalpha():
                cord = d[i+2].split(",")
                skip_next = False
            else:
                cord = d[i+1].split(",")
            cord = [int(float(i)*10) for i in cord]

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
                coordinates.append([last_node[0], cord[0]+last_node[1]])

            elif arg == "h":
                last_node[1] = coordinates[-1][1]
                coordinates.append([last_node[0] + cord[0], last_node[1]])

            elif arg =="l": # Line
                # Cleanup of potential 1
                coordinates[-1] = coordinates[-1][:2]
                doing_bezier = False
                coordinates.append([last_node[0] + cord[0], last_node[1] + cord[1]])

            elif arg =="c": # Bezier line
                controll_points_left = 2
                doing_bezier = True
                if len(coordinates[-1]) == 2:
                    coordinates[-1].append(1)
                coordinates.append([last_node[0] + cord[0], last_node[1] + cord[1]])

            elif arg =="z": # Close curve
                # Cleanup of potential 1
                coordinates[-1] = coordinates[-1][:2]
                coordinates.append([start_point[0], start_point[1], 18])
                start_point = [start_point[0] + cord[0], start_point[1] + cord[1]]

            elif arg =="m": # Relative coordinates
                doing_bezier = False
                start_point = [last_node[0] + cord[0], last_node[1] + cord[1]]
                coordinates.append(start_point)

            else:
                print(d)


        else:
            cord = [int(float(i)*10) for i in item.split(",")]
            if doing_bezier:
                if controll_points_left==0:
                    controll_points_left = 3
                    last_node = coordinates[-1]
                controll_points_left-=1
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


    coordinates[-1] = coordinates[-1][:2]

    str_coord =  ";".join([" ".join([str(i) for i in s]) for s in coordinates])
    # Create the XML structure
    obj = ET.Element('object', type="1", symbol=symbol_mapping["#000000"])
    coords = ET.SubElement(obj, 'coords', count=str(len(coordinates)))
    coords.text = str_coord + ' 18;'  # or 16??
    pattern = ET.SubElement(obj, 'pattern', rotation="0")
    coord = ET.SubElement(pattern, 'coord', x="0", y="0")

    # Replace the original path element with the new XML structure
    # path.getparent().replace(path, obj)
    output_objects.append(obj)

# Create a new tree for the output XML
output_tree = ET.ElementTree(output_objects)

# Save the modified XML to the output file
output_tree.write('output.xml', encoding="utf-8", xml_declaration=True)

with open('output.xml', 'r') as file:
    xml_content = file.read()
    xml_content = xml_content.replace('</object>', '</object>\n')

with open('output.xml', 'w') as file:
    file.write(xml_content)