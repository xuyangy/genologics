
Scripts in the Genologics Package
=================================
Short usage descriptions for the scripts in the Genologics Package.

attach_caliper_files.py
-----------------------
Automated help message generated from running attach_caliper_files.py with the --help flag::

	usage: attach_caliper_files.py [-h] [--pid PID] [--log LOG] [--path PATH]
	
	EPP script to fetch and upload Caliper image files for Clarity LIMS. Searches
	the directory given by the path argument for filenames matching a specific
	pattern ending with: ${INPUT.CONTAINER.PLACEMENT}_${INPUT.NAME}_${INPUT.CONTAI
	NER.LIMSID}_${INPUT.LIMSID}. This is done for each artifact of type
	ResultFile, that is of type PerInput. Any file found matching is copied to the
	current working directory with a name suffixed with the output artifact it is
	connected to. When executed as an EPP, this will cause the Clarity LIMS EPP
	wrapper to associate the file with this artifact. Written by Johannes
	Alneberg, Science for Life Laboratory, Stockholm, Sweden.
	
	optional arguments:
	  -h, --help   show this help message and exit
	  --pid PID    Lims id for current Process
	  --log LOG    Log file for runtime info and errors
	  --path PATH  Path where image files are located

copy_field_art2samp.py
----------------------
Automated help message generated from running copy_field_art2samp.py with the --help flag::

	usage: copy_field_art2samp.py [-h] [--pid PID] [--log LOG] [-s SOURCE_UDF]
	                              [-d DEST_UDF] [-c STATUS_CHANGELOG]
	
	EPP script to copy user defined field from analyte level to submitted sample
	level in Clarity LIMS. Can be executed in the background or triggered by a
	user pressing a "blue button". This script can only be applied to processes
	where ANALYTES are modified in the GUI. The script can output two different
	logs, where the status_changelog contains notes with the technician, the date
	and changed status for each copied status. The regular log file contains
	regular execution information. Error handling: If the udf given is blank or
	not defined for any of the inputs, the script will log this, and not perform
	any changes for that artifact. Written by Johannes Alneberg, Science for Life
	Laboratory, Stockholm, Sweden
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --pid PID             Lims id for current Process
	  --log LOG             File name for standard log file, for runtime
	                        information and problems.
	  -s SOURCE_UDF, --source_udf SOURCE_UDF
	                        Name of the source user defined field that willbe
	                        copied.
	  -d DEST_UDF, --dest_udf DEST_UDF
	                        Name of the destination user defined field that willbe
	                        written to. This argument is optional, if left
	                        emptythe source_udf argument is used instead.
	  -c STATUS_CHANGELOG, --status_changelog STATUS_CHANGELOG
	                        File name for status changelog file, for concise
	                        information on who, what and when for status change
	                        events. Prepends the old changelog file by default.

copy_field_proc2projs.py
------------------------
Automated help message generated from running copy_field_proc2projs.py with the --help flag::

	usage: copy_field_proc2projs.py [-h] [--pid PID] [--log LOG] [-s SOURCE_UDF]
	                                [-d DEST_UDF] [-c STATUS_CHANGELOG]
	
	EPP script to copy user defined field from any process to associated
	project/projects in Clarity LIMS. If the specifyed process handles many
	artifacts associated to different projects, all these projects will get the
	specifyed udf. Can be executed in the background or triggered by a user
	pressing a "blue button". The script can output two different logs, where the
	status_changelog contains notes with the technician, the date and changed
	status for each copied status. The regular log file contains regular execution
	information. Written by Maya Brandi
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --pid PID             Lims id for current Process
	  --log LOG             File name for standard log file, for runtime
	                        information and problems.
	  -s SOURCE_UDF, --source_udf SOURCE_UDF
	                        Name of the source user defined fieldthat will be
	                        copied.
	  -d DEST_UDF, --dest_udf DEST_UDF
	                        Name of the destination user definedfield that will be
	                        written to. Thisargument is optional, if left emptythe
	                        source_udf argument is used instead.
	  -c STATUS_CHANGELOG, --status_changelog STATUS_CHANGELOG
	                        File name for status changelog file, forconcise
	                        information on who, what and whenfor status change
	                        events. Prepends the old changelog file by default.

copy_reference_genome.py
------------------------
Automated help message generated from running copy_reference_genome.py with the --help flag::

	usage: copy_reference_genome.py [-h] [--pid PID] [--log LOG]
	
	EPP script to copy user defined field 'Reference Genome' from project level to
	submitted sample level for the input artifacts of given process, in Clarity
	LIMS. Can be executed in the background or triggered by a user pressing a
	"blue button". The script outputs a regular log file that contains regular
	execution information. Error handling: If the udf 'Reference Genome' is blank
	or not defined for any of the input projects, the script will log this, and
	not perform any changes for that sample. Written by Johannes Alneberg, Science
	for Life Laboratory, Stockholm, Sweden
	
	optional arguments:
	  -h, --help  show this help message and exit
	  --pid PID   Lims id for current Process
	  --log LOG   File name for standard log file, for runtime information and
	              problems.

copy_udf_to_sample.py
---------------------
Automated help message generated from running copy_udf_to_sample.py with the --help flag::

	usage: copy_udf_to_sample.py [-h] [--pid PID] [--log LOG] [-s SOURCE_UDF]
	                             [-d DEST_UDF] [-c STATUS_CHANGELOG] [-a]
	
	EPP script to copy user defined field from analyte level to submitted sample
	level in Clarity LIMS. Can be executed in the background or triggered by a
	user pressing a "blue button". This script can only be applied to processes
	where ANALYTES are modified in the GUI. The script can output two different
	logs, where the status_changelog contains notes with the technician, the date
	and changed status for each copied status. The regular log file contains
	regular execution information. Error handling: If the udf given is blank or
	not defined for any of the inputs, the script will log this, and not perform
	any changes for that artifact. Written by Johannes Alneberg, Science for Life
	Laboratory, Stockholm, Sweden
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --pid PID             Lims id for current Process
	  --log LOG             File name for standard log file, for runtime
	                        information and problems.
	  -s SOURCE_UDF, --source_udf SOURCE_UDF
	                        Name of the source user defined field that willbe
	                        copied.
	  -d DEST_UDF, --dest_udf DEST_UDF
	                        Name of the destination user defined field that willbe
	                        written to. This argument is optional, if left
	                        emptythe source_udf argument is used instead.
	  -c STATUS_CHANGELOG, --status_changelog STATUS_CHANGELOG
	                        File name for status changelog file, for concise
	                        information on who, what and when for status change
	                        events. Prepends the old changelog file by default.
	  -a, --aggregate       Use this tag if your process is aggregating results.
	                        The default behaviour assumes it is the output
	                        artifact of type analyte that is modified while this
	                        tag changes this to using input artifacts instead.

molar_concentration.py
----------------------
Automated help message generated from running molar_concentration.py with the --help flag::

	usage: molar_concentration.py [-h] [--pid PID] [--log LOG] [--aggregate]
	
	EPP script to calculate molar concentration given the weight concentration, in
	Clarity LIMS. Before updating the artifacts, the script verifies that
	'Concentration' and 'Size (bp)' udf:s are not blank, and that the 'Conc.
	units' field is 'ng/ul' for each artifact. Artifacts that do not fulfill the
	requirements, will not be updated. Written by Johannes Alneberg, Science for
	Life Laboratory, Stockholm, Sweden
	
	optional arguments:
	  -h, --help   show this help message and exit
	  --pid PID    Lims id for current Process
	  --log LOG    File name for standard log file, for runtime information and
	               problems.
	  --aggregate  Use this tag if your process is aggregating results. The
	               default behaviour assumes it is the output artifact of type
	               analyte that is modified while this tag changes this to using
	               input artifacts instead

qc_amount_calculation.py
------------------------
Automated help message generated from running qc_amount_calculation.py with the --help flag::

	usage: qc_amount_calculation.py [-h] [--pid PID] [--log LOG] [--aggregate]
	
	EPP script to calculate amount in ng from concentration and volume udf:s in
	Clarity LIMS. The script checks that the 'Volume (ul)' and 'Concentration'
	udf:s are defined and that the udf. 'Conc. Units' have the correct value:
	'ng/ul', otherwise that artifact is skipped, left unchanged, by the script.
	Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden
	
	optional arguments:
	  -h, --help   show this help message and exit
	  --pid PID    Lims id for current Process
	  --log LOG    Log file for runtime info and errors.
	  --aggregate  Use this tag if current Process is an aggregate QC step

zebra_barcodes.py
-----------------
Automated help message generated from running zebra_barcodes.py with the --help flag::

	usage: zebra_barcodes.py [-h] [--container_id] [--operator_and_date]
	                         [--container_name] [--process_name] [--copies COPIES]
	                         [--pid PID] [--log LOG] [--use_printer]
	                         [--hostname HOSTNAME] [--destination DESTINATION]
	                         [--no_prepend]
	
	Print barcodes on zebra barcode printer, different label types available.
	Information is fetched from Clarity LIMS.
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --container_id        Print output container id label in both barcode format
	                        and human readable.
	  --operator_and_date   Print label with both operator and todays date.
	  --container_name      Print label with human readablecontainer name (user
	                        defined)
	  --process_name        Print label with human readableprocess name
	  --copies COPIES       Number of printout copies, only used if neither
	                        container_name nor container_id type labels are
	                        printed. In that case, print one label of each type
	                        for each container.
	  --pid PID             The process LIMS id.
	  --log LOG             File name to use as log file
	  --use_printer         Print file on default or supplied printer using lp
	                        command.
	  --hostname HOSTNAME   Hostname for lp CUPS server.
	  --destination DESTINATION
	                        Name of printer.
	  --no_prepend          Do not prepend old log, useful when ran locally

generate_script_docs.py
-----------------------
Automated help message generated from running generate_script_docs.py with the --help flag::

	usage: generate_script_docs.py [-h]
	
	Generates basic documentation on all scripts contained in the scripts folder.
	Used instead of sphinx extension since readthedocs build failed on genologics
	imports.
	
	optional arguments:
	  -h, --help  show this help message and exit

