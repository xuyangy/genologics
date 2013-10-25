
Scripts in the Genologics Package
=================================
Short usage descriptions for the scripts in the Genologics Package.

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

copy_status_to_sample.py
------------------------
Automated help message generated from running copy_status_to_sample.py with the --help flag::

	usage: copy_status_to_sample.py [-h] [--pid PID] [--log LOG]
	                                [--status_changelog STATUS_CHANGELOG]
	
	EPP script to copy user defined field 'Status (manual)' from analyte level to
	submitted sample level in Clarity LIMS. Can be executed in the background or
	triggered by a user pressing a "blue button". This script can only be applied
	to processes where ANALYTES are modified in the GUI. The script can output two
	different logs, where the status_changelog contains notes with the technician,
	the date and changed status for each copied status. The regular log file
	contains regular execution information. Error handling: If the udf 'Status
	(manual)' is blank or not defined for any of the inputs, the script will log
	this, and not perform any changes for that artifact. Written by Johannes
	Alneberg, Science for Life Laboratory, Stockholm, Sweden
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --pid PID             Lims id for current Process
	  --log LOG             File name for standard log file, for runtime
	                        information and problems.
	  --status_changelog STATUS_CHANGELOG
	                        File name for status changelog file, for concise
	                        information on who, what and when for status change
	                        events. Prepends the old changelog file by default.

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
	  --container_id        Print container id label in both barcode format and
	                        human readable.
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

