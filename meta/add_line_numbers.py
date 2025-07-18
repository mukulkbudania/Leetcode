import csv

input_file = 'input.csv'
output_file = '18_07_2025_Last3Months.csv'

with open(input_file, 'r', encoding='utf-8') as infile, \
     open(output_file, 'w', newline='', encoding='utf-8') as outfile:
    
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    # Read header from input
    header = next(reader)
    
    # Write new header: fqRanking + original header
    writer.writerow(['FqRanking'] + header)
    
    # Add line numbers starting from 1
    for idx, row in enumerate(reader, start=1):
        writer.writerow([idx] + row)