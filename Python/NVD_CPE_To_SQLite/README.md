# NIST NVD CPE to SQLite3 conversion.

Rather simple tool that works as follows:

1. Calls out to `cpe_v23_url` to fetch the latest CPE Dictionary ZIP file and places it in the cache folder located in the script execution directory.
2. Unzips it in a cache folder created in the script execution directory.
3. Parses the XML document dumped by the `zipfile` library and loads it into memory.
4. Parsed XML document is then passed to `parse_root` function where a `dict` containing CVE information is returned.
5. `cpe.db` is created in the script execution directory with a table called `cpe`.
6. Data inside the `dict` is inserted into the `cpe` table.

## External Libraries Used:

- [alive-progress](https://pypi.org/project/alive-progress/) - To display the progress bar when inserting data inside the SQLite database.
- [requests](https://pypi.org/project/requests/) - For downloading the CPE zip file.

## References:

- [Official CPE Dictionary](https://nvd.nist.gov/products/cpe)
- [xml.etree.elementtree Reference](https://docs.python.org/3/library/xml.etree.elementtree.html#)
