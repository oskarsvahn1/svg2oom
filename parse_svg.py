import xml.etree.ElementTree as ET

# Load the SVG file
tree = ET.parse('line.svg')
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

    # If the fill color is in the symbol mapping, continue with the conversion
    #if fill_color in symbol_mapping:
        # Get the 'd' attribute value
    d = path.get('d')
    args = []
    coordinates = []
    # Split the 'd' attribute into coordinates
    # d.replace(" C",",0.001").replace(" ",";").replace(",", " ").replace("M;", "").replace(".", "")
    # hej=d.replace(" C",",1").replace("M ","").split(" ")

    replace_front = ['C', 'c', 'h', 'H', 'v', 'V', 'l', 'L', 'm']
    for char in replace_front:
        d = d.replace(char+" ", char+',')


    d = d.replace("M ", "").replace("z m", "zm").split(" ")
    controll_points_left = 0
    last_cord_x = 0
    last_cord_y = 0
    abs_cord = [0, 0]
    last_node = [0, 0]

    start_point = [0, 0]
    is_rel_coord = True
    doing_bezier = False
    for i, cord in enumerate(d):
        if i==5:
            pass
        cord = cord.split(",")
        if cord[0].isalpha():
            cord_int = [int(float(i)*10) for i in cord[1:]]

            if cord[0] == "v":
                node = [last_node[0], int(float(cord[1])*10)+last_node[1]]
                coordinates.append(node)
                last_node = node
            elif cord[0] == "V":
                node = [last_node[0], int(float(cord[1])*10)]
                coordinates.append(node)
                last_node = node
            elif cord[0] == "h":
                node = [last_node[0] + int(float(cord[1])*10), last_node[1]]
                coordinates.append(node)
                last_node = node
            elif cord[0] == "H":
                node = [int(float(cord[1])*10), last_node[1]]
                coordinates.append(node)
                last_node = node
            elif cord[0] =="l": # Relative line
                doing_bezier = False
                is_rel_coord = True
                node = [last_node[0] + int(float(cord[1])*10), last_node[1] + int(float(cord[2])*10)]
                coordinates.append(node)
                last_node = node

            elif cord[0] =="L": # Absolute line
                doing_bezier = False
                is_rel_coord = False
                node = [int(float(cord[1])*10), int(float(cord[2])*10)]
                coordinates.append(node)
                last_node = node

            elif cord[0] =="C": # Absolute coordinates
                controll_points_left = 3
                is_rel_coord = False
                doing_bezier = True

                coordinates[-1].append(1)
                coordinates.append(cord_int)
                last_node = coordinates[-2][:2]

            elif cord[0] =="c": # Relative coordinates
                controll_points_left = 3
                is_rel_coord = True
                doing_bezier = True
                coordinates[-1].append(1)
                coordinates.append([last_node[0] + cord_int[0], last_node[1] + cord_int[1]])
                last_node = coordinates[-2][:2]


            elif cord[0] =="zm": # Relative coordinates
                is_rel_coord = True
                coordinates.append([start_point[0], start_point[1], 18])

                coordinates.append([start_point[0] + cord_int[0], start_point[1] + cord_int[1]])
                start_point = [start_point[0] + cord_int[0], start_point[1] + cord_int[1]]
                last_node = coordinates[-1]


            
            elif cord[0] =="m": # Relative coordinates
                start_point = cord_int
                is_rel_coord = True
                coordinates.append([last_node[0] + cord_int[0], last_node[1] + cord_int[1]])
                last_node = coordinates[-1]

            else:
                print(d)

        elif controll_points_left==0 and doing_bezier:
            cord_int = [int(float(i)*10) for i in cord]
            coordinates[-1].append(1)
            last_node = coordinates[-1][:2]
            if is_rel_coord:
                coordinates.append([last_node[0] + cord_int[0], last_node[1] + cord_int[1]])
            else:
                coordinates.append([cord_int[0], cord_int[1]])
            controll_points_left = 3

        else:
            cord_int = [int(float(i)*10) for i in cord]

            if is_rel_coord:
                coordinates.append([last_node[0] + cord_int[0], last_node[1] + cord_int[1]])
                if not doing_bezier:
                    last_node = coordinates[-1][:2]

            else:
                coordinates.append(cord_int)
                if not doing_bezier:
                    last_node = coordinates[-1][:2]
            if controll_points_left==1:
                last_node = coordinates[-1][:2]


        controll_points_left-=1
            

        if len(last_node) ==1:
            pass

        # else:    
        #     cord_int = [int(float(i)*10) for i in cord[:2]]

        #     cord[:2] = [float(i) for i in cord[:2]]
        #     if len(cord)==3:
        #         if cord[2] =="C": # Absolute coordinates
        #             is_rel_coord = False
        #             coordinates.append([cord_int[0], cord_int[1], 1])
        #             controll_points_left = 3
        #         elif cord[2] =="c": # Relative coordinates
        #             controll_points_left = 3
        #             is_rel_coord = True
        #             coordinates.append([cord_int[0], cord_int[1], 1])
        #             last_node = cord_int
        #         else:
        #             print(cord)

        #     elif controll_points_left==0:
        #         if is_rel_coord:
        #             coordinates.append([last_node[0] + cord_int[0], last_node[1] + cord_int[1], 1])
        #         else:
        #             coordinates.append([cord_int[0], cord_int[1], 1])
        #         controll_points_left = 3
        #         last_node = coordinates[-1][:2]

        #     else:
        #         if is_rel_coord:
        #             coordinates.append([last_node[0] + cord_int[0], last_node[1] + cord_int[1]])
        #         else:
        #             coordinates.append(cord_int)

        #     controll_points_left-=1

    # result = [[float(i)*1000 for i in s.split(",")] for s in hej]

    coordinates.append(start_point)

    coordinates[-1] = coordinates[-1][:2]

    # coordinates = [[sublist[0], sublist[1], sublist[2]] if len(sublist) > 2 else [sublist[0], -sublist[1]] for sublist in coordinates]
    str_coord =  ";".join([" ".join([str(i) for i in s]) for s in coordinates])
    # Create the XML structure
    obj = ET.Element('object', type="1", symbol=symbol_mapping["#000000"])
    coords = ET.SubElement(obj, 'coords', count=str(len(coordinates)))
    coords.text = str_coord + ' 16;'
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