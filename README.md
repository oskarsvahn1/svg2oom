# svg2oom
Short handmade script to convert a SVG-file to OOM, in progress

To run the script, type

    python parse_svg.py <inputfile.svg> <outputfile.omap> [--scale] [--flip_y] [--as_point]
like

    python parse_svg.py input.svg
or

    python parse_svg.py input.svg out.omap --scale 400 --flip_y --as_point 

to save the file as out.omap, upscaled 400 times, and with the  y-direction reversed.

It the script fails to recreate the svg file, try to open the file in Inkscape, convert all objects to path, and save as Inkscape svg before trying again.

