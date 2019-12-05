"""
This file contains helper functions for evaluate_segmentation.py script.
"""

import os
import xml.etree.cElementTree as ET
import csv
import numpy as np
import subprocess

# compare segmentations based on the EvaluateSegmentation software of Taha
from Full_vasculature.Utils import config


def segment_comparison(goldstandard_path, segmentation_path, executable_path, eval_result_path, threshold, measures):
	print(measures)
	command_string = executable_path + " \"" + goldstandard_path + "\" \"" + segmentation_path + "\" -use " + measures + " -xml \"" + eval_result_path + "\" -thd " + str(threshold)
	print(command_string)
	os.system(command_string)

# parse the xml file and create dataframes for the relevant metric data. Also, save the dataframe data into csvs
def parse_xml_to_csv(xml_path, csv_path, run_params=None):
	# get all the metrics as a list
	if run_params is None:
		run_params = {}
	list_of_measures = []
	measures_values = []
	tree = ET.parse(xml_path)
	root = tree.getroot()
	for child in root.findall(".//metrics/*"):
		list_of_measures.append(child.attrib["symbol"])
		value = child.attrib["value"]
		measures_values.append(value)

	with open(csv_path, 'a+') as f1:
		writer = csv.writer(f1)
		if os.path.isfile(csv_path) and os.path.getsize(csv_path) == 0:
			writer.writerow(list(run_params.keys()) + list_of_measures)
		writer.writerow(list(run_params.values()) + measures_values)


# calculate_sensibility
def calculate_sensibility(metrics_dic):
	try:
		fp = int(metrics_dic["FP"])
		fn = int(metrics_dic["FN"])
		tp = int(metrics_dic["TP"])
		valsensibility = (1 - fp / (tp + fn)) * 100
	except (KeyError, ZeroDivisionError):
		valsensibility = np.nan

	return round(valsensibility, 6)


# calculate_conformity
def calculate_conformity(metrics_dic):
	try:
		fp = int(metrics_dic["FP"])
		fn = int(metrics_dic["FN"])
		tp = int(metrics_dic["TP"])
		valconformity = (1 - (fp + fn) / tp) * 100
	except (KeyError, ZeroDivisionError):
		valconformity = np.nan

	return round(valconformity, 6)


# create dictionary of
def create_dict_from_xml(xml_path, metrics_list=None):
	if metrics_list is None:
		metrics_list = ["TP", "FP", "TN", "FN"]

	value_metrics_dic = []
	tree = ET.parse(xml_path)
	root = tree.getroot()
	for child in root.findall(".//metrics/*"):
		if child.tag in metrics_list:
			value_metrics_dic.append(child.attrib["value"])
	metrics_dic = dict(zip(metrics_list, value_metrics_dic))
	return metrics_dic


def sensibility_conformity_to_xml(xml_path):
	"""
	Insert Sensibility and Conformity values into Evaluation xml.

	:param xml_path: path to xml file generated by EvaluateSegmentation.exe
	"""
	print('ADDING SENSBIL and CFM to:', xml_path)
	tree = ET.parse(xml_path)
	root = tree.getroot()

	metrics_dic = create_dict_from_xml(xml_path)

	valsensibility = calculate_sensibility(metrics_dic)
	valconformity = calculate_conformity(metrics_dic)

	sensibility_attributes = {"name": "sensibility", "value": str(valsensibility), "symbol": "SENSBIL",
							  "type": "similarity", "unit": "voxel"}
	SENSBIL = ET.Element("SENSBIL", attrib=sensibility_attributes)
	conformity_attributes = {"name": "conformity", "value": str(valconformity), "symbol": "CFM", "type": "similarity",
							 "unit": "voxel"}
	CFM = ET.Element("CFM", attrib=conformity_attributes)

	root[2].insert(2, SENSBIL)
	root[2].insert(3, CFM)
	tree.write(xml_path)


# noinspection PyTypeChecker
def parse_xml_to_csv_avg_for_patients(xml_paths, csv_path, run_params):
	measures_values_all_patients = []
	# get all the metrics as a list
	measures_symbols = []
	for i, path in enumerate(xml_paths):
		measures_values = []
		tree = ET.parse(path)
		root = tree.getroot()
		for child in root.findall(".//metrics/*"):
			if i == 0:
				measures_symbols.append(child.attrib["symbol"])
			measures_values.append(child.attrib["value"])
		measures_values_all_patients.append(measures_values)

	# count average for each metric
	measures_values_avg = np.mean(np.asarray(measures_values_all_patients, dtype=np.float32), axis=0)
	print(measures_values_avg)

	with open(csv_path, 'a+') as f1:
		writer = csv.writer(f1)
		if os.path.isfile(csv_path) and os.path.getsize(csv_path) == 0:
			writer.writerow(list(run_params.keys()) + measures_symbols)
		writer.writerow(list(run_params.values()) + measures_values_avg.tolist())


def evaluate_segmentation(label_path, segmentation_path, threshold, executable_path, xml_path_patient, measures):

	# compare the segmentation with ground truth and save the xml file in the results folder
	segment_comparison(label_path, segmentation_path, executable_path, xml_path_patient, threshold, measures)

	# parse the generated xmls and insert two more metrics: Sensibility and Conformity
	sensibility_conformity_to_xml(xml_path_patient)
	
