from __future__ import division
import argparse
import numpy as np
import pandas as pd
import pysam
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict


def main():
	"""Main program"""
	args = parse_args()
	samfile = pysam.AlignmentFile(args.bam, "rb")
	for chromosome in args.chromosomes:
		data = traverse_bam(samfile, chromosome, args.window_size, args.min_depth,
							args.min_minor_depth, args.min_minor_fraction, 10, 0.05)
		plot_data(data)


def parse_args():
	parser = argparse.ArgumentParser(description="Add description")
	parser.add_argument("--bam", required=True, help="Input bam file")
	parser.add_argument("--chromosomes", "-c", nargs="+", default=["chrX", "chrY", "chr19"],
						help="Chromosomes to analyze.")
	parser.add_argument("--window_size", "-w", type=int, default=50000,
						help="Window size (integer) for sliding window calculations.")
	parser.add_argument("--min_depth", "-d", type=int, default=2,
						help="Minimum depth for a site to be considered.")
	parser.add_argument("--min_minor_depth", "-ar", type=int, default=1,
						help="Minimum number of reads supporting the alternate allele to be considered.")
	parser.add_argument("--min_minor_fraction", "-af", type=float, default=0.1,
						help="Minimum fraction of reads supporting the alternate allele to be considered.")
	args = parser.parse_args()
	return args


def get_length(samfile, chrom):
	"""Extract chromosome length from BAM header.

	Args:
		samfile: pysam AlignmentFile object
		chromosome: Chromosome name (string)

	Returns:
		Length (int)
	"""
	lengths = dict(zip(samfile.references, samfile.lengths))
	return lengths[chrom]


def reset_lists(n, size):
	"""Initialize `n` lists of size `size`."""
	return [[0] * size for i in range(n)]


def reset_counters(n):
	"""Initialize `n` lists of size `size`."""
	return [Counter() for i in range(n)]


def traverse_bam(samfile, chrom, window_size, min_depth, min_minor_depth,
					min_minor_fraction, depth_binsize, readbal_binsize):
	"""Analyze the `samfile` BAM file for various metrics and statistics.

	Currently, this function looks at the following metrics:
	- Read depth
	- Read balance (allelic fractions)
	- Mapping quality

	For each metric, a pandas data frame will be created with frequencies
	across a number of ranges (for plotting a histogram).

	The average of each metric will also be calculated for each window of
	size `window_size` and stored altogether in a pandas data frame.

	Returns a dictionary of pandas data frames with the following keys:
	- depth_freq: Frequencies of read depths
	- readbal_freq: Frequencies of read balances
	- mapq_freq: Frequencies of mapping qualities
	- windows: The averages for each metric for each window
	"""
	chr_len = get_length(samfile, chrom)
	num_windows = chr_len // window_size + 1
	depths, readbals, mapqs = reset_lists(3, window_size)
	depths_binned, readbals_binned, mapqs_binned = reset_lists(3, window_size)
	depths_counter, readbals_counter, mapqs_counter = reset_counters(3)
	window_id = 0
	win_pos = 0
	for chr_pos, column in enumerate(samfile.pileup(chrom, 0, chr_len)):
		base_counter = defaultdict(int)
		col_mapqs = []

		# Iterate over reads in the pileup column
		for read in column.pileups:
			if not read.is_del and not read.is_refskip:
				base = read.alignment.query_sequence[read.query_position]
				base_counter[base] += 1
				col_mapqs.append(read.alignment.mapping_quality)

		# Identify major and minor allele counts
		base_counts = sorted(base_counter.values(), reverse=True)
		num_major = 0 if len(base_counts) < 1 else base_counts[0]
		num_minor = 0 if len(base_counts) < 2 else base_counts[1]
		total_depth = num_major + num_minor

		# Apply threshold and track metrics
		if total_depth >= min_depth:
			depths[win_pos] = total_depth
			mapqs[win_pos] = sum(col_mapqs) / len(col_mapqs)  # Mean
			allele_fraction = num_minor / total_depth
			if num_minor >= min_minor_depth and allele_fraction >= min_minor_fraction:
				readbals[win_pos] = allele_fraction

		# Increment counters
		win_pos += 1
		chr_pos += 1

		# Are we at the end of a window?
		if win_pos == window_size - 1:
			# Bin values
			depths_binned[window_id] = np.mean(np.asarray(depths))
			readbals_binned[window_id] = np.mean(np.asarray(readbals))
			mapqs_binned[window_id] = np.mean(np.asarray(mapqs))
			# Increment counters
			depths_counter.update(depths)
			readbals_counter.update(readbals)
			mapqs_counter.update(mapqs)
			# Reset and increment
			num_passed_depth = len(depths)
			num_passed_minor = len(readbals)
			depths, readbals, mapqs = reset_lists(3, window_size)
			win_pos = 0
			window_id += 1
			# Print progress
			print "{} out of {} positions passed depth threshold.".format(num_passed_depth, window_size)
			print "{} out of {} positions passed minor allele thresholds.".format(num_passed_minor, window_size)
			print "{} out of {} windows processed.".format(window_id, num_windows)

	# Convert data into pandas data frames
	windows_df = pd.DataFrame({
		"depth": np.asarray(depths_binned),
		"readbal": np.asarray(readbals_binned),
		"mapq": np.asarray(mapqs_binned)
	})

	mapq_freq_df = pd.DataFrame(dict(zip(np.asarray(mapqs_counter.keys()),
											np.asarray(mapqs_counter.values()))))

	# TODO: Create depth_freq_df and readbal_freq_df data frames

	results = {
		"windows": windows_df,
		"mapq_freq": mapq_freq_df
	}
	return results


def plot_data(dataDict):
	"""
	Takes a dictionary (output from traverseBam) and outputs histograms and
	genome-wide plots of various metrics
	"""

	window_df = dataDict["windows"]
	depth_hist = dataDict["depth_freq"]
	readbal_hist = dataDict["readbal_freq"]
	mapq_hist = dataDict["mapq_freq"]

	# Create genome-wide plots based on window means
	depth_genome_plot = sns.lmplot('Position', 'Depth', data=window_df, fit_reg=False)
	depth_genome_plot.savefig("depth_windows.png")

	balance_genome_plot = sns.lmplot('Position', 'ReadBalance', data=window_df, fit_reg=False)
	balance_genome_plot.savefig("balance_windows.png")

	mapq_genome_plot = sns.lmplot('Position', 'ReadBalance', data=window_df, fit_reg=False)
	mapq_genome_plot.savefig("mapq_windows.png")

	# Create histograms
	depth_bar_plot = sns.countplot(x='Depth', y='Count', data=depth_hist)
	depth_bar_plot.savefig("depth_hist.png")

	balance_bar_plot = sns.countplot(x='ReadBalance', y='Count', data=readbal_hist)
	balance_bar_plot.savefig("readbalance_hist.png")

	mapq_bar_plot = sns.countplot(x='Mapq', y='Count', data=mapq_hist)
	mapq_bar_plot.savefig("mapq_hist.png")

	pass


if __name__ == "__main__":
	main()
