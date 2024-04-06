import requests
import zipfile
import os
import time
import sqlite3
import xml.etree.ElementTree as ET
import alive_progress

# Constants
cache_folder_path = 'cache/'
cpe_zip_file = 'cpe-dictionary_v2.3.xml.zip'
cpe_dictionary_file = 'official-cpe-dictionary_v2.3.xml'
cpe_v23_url = 'https://nvd.nist.gov/feeds/xml/cpe/dictionary/official-cpe-dictionary_v2.3.xml.zip'

# Functions
def pretty_print(msg):
  print('--- ' + msg + ' ---')

def download_cpe_dictionary():
  if(os.path.exists(cache_folder_path + 'cpe_v23.zip') and (time.time() - os.path.getmtime(cache_folder_path + 'cpe_v23.zip')) < 86400):
    pretty_print('CPE info already downloaded in the last 24 hours. Skipping...')
    return

  pretty_print('Downloading latest CPE info...')
  response = requests.get(cpe_v23_url)
  with open(cache_folder_path + 'cpe_v23.zip', 'wb') as f:
    f.write(response.content)
  pretty_print('Downloaded latest CPE info to ' + cache_folder_path + 'cpe_v23.zip')

def extract_cpe_dictionary():
  pretty_print('Extracting CPE info...')
  with zipfile.ZipFile(cache_folder_path + 'cpe_v23.zip', 'r') as zip_ref:
    zip_ref.extractall(cache_folder_path)
  pretty_print('Extracted CPE info to "' + cache_folder_path + '"')

def parse_cpe_dictionary() -> ET:
  pretty_print('Parsing CPE info, please wait...')
  return ET.parse(cache_folder_path + 'official-cpe-dictionary_v2.3.xml')

def prase_root(root) -> dict:
  cpe_dict = {}
  for cpe_item in root.findall('{http://cpe.mitre.org/dictionary/2.0}cpe-item'):
    cpe_title = cpe_item.find('{http://cpe.mitre.org/dictionary/2.0}title').text
    cpe23_item = cpe_item.find('{http://scap.nist.gov/schema/cpe-extension/2.3}cpe23-item').attrib['name']
    cpe23_item_array = cpe23_item.split(':')
    cpe_dict[cpe_title] = {
      'cpe_version': cpe23_item_array[1],
      'part': cpe23_item_array[2],
      'vendor': cpe23_item_array[3],
      'product': cpe23_item_array[4],
      'version': cpe23_item_array[5],
      'update': cpe23_item_array[6],
      'edition': cpe23_item_array[7],
      'language': cpe23_item_array[8],
      'sw_edition': cpe23_item_array[9],
      'target_sw': cpe23_item_array[10],
      'target_hw': cpe23_item_array[11],
      'other': cpe23_item_array[12]
    }
  return cpe_dict

# Main
if __name__ == '__main__':
  download_cpe_dictionary()
  extract_cpe_dictionary()
  cpe_tree = parse_cpe_dictionary()
  cpe_dict = prase_root(cpe_tree.getroot())

  pretty_print('CPE info loaded')
  pretty_print('Loading CPE info into cpe.db')
  conn = sqlite3.connect('cpe.db')
  c = conn.cursor()
  c.execute('CREATE TABLE IF NOT EXISTS cpe (title text, cpe_version text, part text, vendor text, product text, version text, cve_update text, edition text, language text, sw_edition text, target_sw text, target_hw text, other text)')
  with alive_progress.alive_bar(len(cpe_dict),bar='bubbles') as bar:
    for cpe_title, cpe_info in cpe_dict.items():
      c.execute('INSERT OR REPLACE INTO cpe VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', (cpe_title, cpe_info['cpe_version'], cpe_info['part'], cpe_info['vendor'], cpe_info['product'], cpe_info['version'], cpe_info['update'], cpe_info['edition'], cpe_info['language'], cpe_info['sw_edition'], cpe_info['target_sw'], cpe_info['target_hw'], cpe_info['other']))
      bar()
  conn.commit()
  conn.close()
  pretty_print('CPE info loaded into cpe.db')