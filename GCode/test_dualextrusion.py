import sys, getopt, math

def main(argv):
	inputfile = ''
	outputfile = ''
	e_commands = True
	f_commands = True
	layer_files = False
	on = "M42 P9 S255\n"
	off = "M42 P9 S0\n"
	is_on = False
	curing_passes = 2

	try:
		opts, args = getopt.getopt(argv,"i:o:c:efl",["input=","output="])
	except getopt.GetoptError:
		print("args (all optional): -i <input file> -o <output file> -e -f -l")
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-e':
			print("Removing E commands from T1 GCode")
			e_commands = False
		elif opt == '-f':
			print("Removing F commands from T1 GCode")
			f_commands = False
		elif opt == '-l':
			print("Generating layer files")
			layer_files = True
		elif opt in ("-i", "--input"):
			inputfile = arg
		elif opt in ("-o", "--output"):
			outputfile = arg
		elif opt == '-c':
			curing_passes = int(arg)

	if inputfile == '':
		print("Err: no input file specified")
		sys.exit(2)

	if outputfile == '': # default output file
   	    outputfile = "output.gcode"

	print("Input file:", inputfile)
	print("Output file:", outputfile)
	print()

	input_gcode = open(inputfile, "r")
	output_gcode = open(outputfile, "w") 

	layers = 0
	T1_sections = 0 # number of sections in the GCode using T1
	T1 = False # is the machine currently using the fluid extruder
	layer = False # are we currently writing to layer file
	pos = [0.0,0.0]
	old_pos = [0.0,0.0]
	current_z = 15
	min_cure_height = 0.6
	remove_travel = False
	extruder = ""

	for line in input_gcode: 

		if line.find("Z") != -1:
			z_index = line.find("Z")
			next_space = line.find(" ", z_index)
			if next_space == -1:
				next_space = line.find("\n", z_index)
			#print(line[z_index:next_space])
			current_z = float(line[z_index+1:next_space])

		if T1 and line.find("T"+extruder) == -1 and line.find("T") != -1 and line[1] != "0" and len(line) == 3: # FIX LINE LATER
			output_gcode.write(off)
			copy += off
			if current_z > min_cure_height:
				output_gcode.write("; CURING PASS 1\nT" + extruder + "\nG91\nG0 Z1.0\nG90\n")
				output_gcode.write(copy)
				for i in range(2, curing_passes+1):
					output_gcode.write("; CURING PASS "+str(i)+"\n")
					output_gcode.write(copy)
				#output_gcode.write("G91\nG0 Z-1.0\nG90\n")
				output_gcode.write("; CURING DONE\n")
			extruder = line[1]

		if line.find("T0") == -1 and line.find("T") != -1 and len(line) == 3: # found T1 or other extruder
			extruder = line[1]
			T1 = True
			T1_sections += 1
			T1_write = open("T1_section"+str(T1_sections)+".txt","w")
			copy = ""
			#print("NEW T1")

		if line.find("T0") != -1 and T1: # switching back to T0
			output_gcode.write(off)
			copy += off
			if current_z > min_cure_height:
				output_gcode.write("; CURING PASS 1\nT" + extruder + "\nG91\nG0 Z1.0\nG90\n")
				output_gcode.write(copy)
				for i in range(2, curing_passes+1):
					output_gcode.write("; CURING PASS "+str(i)+"\n")
					output_gcode.write(copy)
				#output_gcode.write("G91\nG0 Z-1.0\nG90\n")
				output_gcode.write("; CURING DONE\n")
			is_on = False
			T1 = False
			T1_write.close()

		if layer_files:
			if line.find("Z") != -1 and line.find("nozzle") == -1: # fix later, doesn't work with Cura's slicer
				if layer:
					layer_gcode.close()
				else:
					layer = True
				layers += 1
				output_gcode.write("; Layer " + str(layers) + "\n")
				layer_gcode = open("layer"+str(layers)+".txt","w")

			if layer:
				if line.find("M107") != -1:
					layer = False
				else:
					layer_gcode.write(line)

		if T1: # fluid extruder GCode
			T1_write.write(line)
			modified_line = line 

			if remove_travel and line.find("G1") != -1 and line.find("E") != -1 and (line.find("X") != -1 or line.find("Y") != -1):
				modified_line = remove_command(modified_line, "E")
				modified_line = "G0" + modified_line[2:]
				remove_travel = False

			if line.find("Z") != -1 and line.find("nozzle") == -1:
				#output_gcode.write("; CURING PASS 1\nT1\nG91\nG0 Z1.0\nG90\n")
				#output_gcode.write(copy)
				#output_gcode.write("; CURING PASS 2\n")
				#output_gcode.write(copy)
				#output_gcode.write("G91\nG0 Z-1.0\nG90\n")
				output_gcode.write(off)
				copy += off
				if current_z > min_cure_height and len(copy.split('\n')) > 3:
					output_gcode.write("; CURING PASS 1\nT" + extruder + "\nG91\nG0 Z1.0\nG90\n")
					output_gcode.write(copy)
					for i in range(2, curing_passes+1):
						output_gcode.write("; CURING PASS "+str(i)+"\n")
						output_gcode.write(copy)
					#output_gcode.write("G91\nG0 Z-1.0\nG90\n")
					copy = ""
					remove_travel = True
					output_gcode.write("; CURING DONE\n")

			if (line.find("G0") != -1 or line.find("G1") != -1) and line.find("X") != -1 and line.find("Y") != -1:
				x_index = line.find("X")
				y_index = line.find("Y")
				#print(line)
				#print(line[x_index+1:line.find(" ",x_index)])
				#print(line[y_index+1:line.find(" ",y_index)])
				pos[0] = float(line[x_index+1:line.find(" ",x_index)])
				pos[1] = float(line[y_index+1:line.find(" ",y_index)])


			if not e_commands and modified_line.find("E") != -1:
				modified_line = remove_command(modified_line, "E") # take out E commands

			if not f_commands and modified_line.find("F") != -1:
				modified_line = remove_command(modified_line, "F") # take out F commands

			if modified_line.find("F") != -1:
				modified_line = slow_down(modified_line, 1000)

			# toggle fluid extruder
			if modified_line.find("G0") != -1 and is_on: # extruding -> traveling
				dist = math.sqrt((pos[0]-old_pos[0])**2+(pos[1]-old_pos[1])**2)
				#print("Traveling a distance of",dist)
				if dist > 1.0:
					output_gcode.write(off) # turn off
					copy += off
					is_on = False
			elif modified_line.find("G1") != -1 and modified_line.find("E") != -1 and not is_on: # traveling -> extruding
				#e_index = line.find("E")
				#if float(line[e_index+1:line.find(" ",e_index)]) > 0.0:
				output_gcode.write(on) # turn on
				copy += on
				is_on = True

			if modified_line.find("G0") != -1 or modified_line.find("G1") != -1:
				old_pos[0] = pos[0]
				old_pos[1] = pos[1]

			#print(modified_line)
			output_gcode.write(modified_line)

			if modified_line.find("F") != -1:
				modified_line = slow_down(modified_line, 200)
			if (modified_line.find("G0") != -1 or modified_line.find("G1") != -1) and modified_line.find("X") != -1 and modified_line.find("Y") != -1:
				#print("NEW LINE")
				#print(modified_line)
				x_index = modified_line.find("X")
				y_index = modified_line.find("Y")
				x = float(modified_line[x_index+1:modified_line.find(" ",x_index)])
				y = float(modified_line[y_index+1:modified_line.find(" ",y_index)])
				#print(x)
				#print(y)
				x = x - 17
				y = y - 50
				modified_line = modified_line[:x_index+1] + format(x, '.3f') + modified_line[modified_line.find(" ", x_index):]
				y_index = modified_line.find("Y")
				modified_line = modified_line[:y_index+1] + format(y, '.3f') + modified_line[modified_line.find(" ", y_index):]
				#print(modified_line)

			if line.find("T") == -1:
				copy += modified_line
			
		else:
			output_gcode.write(line)



	#print(input_gcode.read())
	
	"""
	if T1:
		print("FSDHLKFJDSFKJDs")
		print(copy)
		output_gcode.write(off)
		copy += off
		output_gcode.write("; CURING LAYER\n")
		output_gcode.write(copy)
		output_gcode.write("G91\nG0 Z-1.0\nG90\n")
		is_on = False
		T1 = False
		T1_write.close()
	"""

	if is_on:
		output_gcode.write(off)
		is_on = False

	print("Generated " + str(layers) + " layer files.")
	output_gcode.write("G28\n") # return to home
	output_gcode.close() 

def remove_command(line, char):
	char_index = line.find(char)
	next_space = line.find(" ", char_index)
	extract = line[:char_index]
	if next_space != -1:
		extract = extract + line[next_space+1:]
	return extract + "\n"

def slow_down(line, rate): # slows feed rate to specific rate
	f_index = line.find("F")
	next_space = line.find(" ", f_index)
	if next_space == -1:
		next_space = line.find("\n", f_index)
	#print(line[f_index:next_space])
	extract = line
	if next_space != -1:
		extract = line[:f_index+1]+str(rate)+line[next_space:]
		#print(extract)
	return extract

if __name__ == "__main__":
	main(sys.argv[1:])


