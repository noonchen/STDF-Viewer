#
# DatabaseFetcherRust.py - STDF Viewer
#
# Python wrapper around the Rust DataFetcher.
#
# Mirrors the public API of deps/DatabaseFetcher.py (parity is verified by
# compare_fetchers.py with the "rust" engine). Every SQL statement runs inside
# the Rust DataFetcher; this class only performs the thin container shaping the
# callers expect.
#

import numpy as np
import rust_stdf_helper
from deps.SharedSrc import record_name_dict


class DatabaseFetcherRust:
    def __init__(self):
        self._fetcher = None
        self.file_paths = []

    def connectDB(self, dataBasePath: str, cacheBudgetMB: int | None = None):
        """
        Connect to a session database.

        Args:
            dataBasePath: path of the .db file to open.
            cacheBudgetMB: optional test-data cache budget in MiB; the Rust
                default (128 MiB) is used when omitted or <= 0.
        """
        self.closeDB()
        if cacheBudgetMB is None or (isinstance(cacheBudgetMB, int) and cacheBudgetMB <= 0):
            self._fetcher = rust_stdf_helper.DataFetcher(dataBasePath)
        else:
            self._fetcher = rust_stdf_helper.DataFetcher(
                dataBasePath, cache_budget_mb=int(cacheBudgetMB)
            )
        self.readFilePaths()

    def closeDB(self):
        """Close the current session, if one is connected."""
        if self._fetcher is not None:
            self._fetcher.close()
            self._fetcher = None
        self.file_paths = []

    def checkConnection(self):
        """Raise RuntimeError when no database is connected."""
        if self._fetcher is None:
            raise RuntimeError("No database is connected")

    def readFilePaths(self):
        """(Re)read the file path list of the connected database into ``self.file_paths``."""
        self.checkConnection()
        self.file_paths = self._fetcher.get_file_paths()

    @property
    def num_files(self):
        """Number of files (Fid values) in the connected database."""
        self.checkConnection()
        return self._fetcher.num_files()

    def isDutInfoColumnEmpty(self, columnName: str) -> bool:
        """Return True when no Dut_Info row carries a value for ``columnName``.

        Args:
            columnName: a Dut_Info column name, e.g. "PartText", "WaferIndex", "XCOORD".

        This is used to hide table columns that contain nothing but NULL.
        """
        self.checkConnection()
        return self._fetcher.is_dut_info_column_empty(columnName)

    def getWaferCount(self) -> list[int]:
        """Return the number of wafers per file, indexed by file id.

        A file without any Wafer_Info row counts as 0.
        """
        self.checkConnection()
        return self._fetcher.get_wafer_count()

    def getByteOrder(self) -> list[bool]:
        """Return the byte order of each file as a bool, indexed by file id.

        True means little endian.
        """
        self.checkConnection()
        return self._fetcher.get_byte_order()

    def getTestItemsList(self):
        """Return the test item list in database order.

        Each item is ``"<TEST_NUM>\t#<pmr>\t<TEST_NAME>"`` for an MPR test (the pmr
        index is included) or ``"<TEST_NUM>\t<TEST_NAME>"`` otherwise.
        """
        self.checkConnection()
        return self._fetcher.get_test_items()

    def getTestRecordTypeDict(self):
        """Return ``{(TEST_NUM, TEST_NAME): SUB_CODE}`` for every test in the database.

        Raises:
            ValueError: the same (test number, test name) is registered with two
                different record types, which means the files cannot be merged and
                should be loaded separately.
        """
        self.checkConnection()
        recTypeDict = {}
        for tnum, tname, subcode in self._fetcher.get_test_record_type_rows():
            if (tnum, tname) in recTypeDict and recTypeDict[(tnum, tname)] != subcode:
                previous_rec = recTypeDict[(tnum, tname)]
                raise ValueError(f"{tnum} {tname} is registered as {record_name_dict[previous_rec]}, \
                    but it appears as {record_name_dict[subcode]} again.\nIf you are opening multiple files, \
                    you should open them separately.")
            else:
                recTypeDict[(tnum, tname)] = subcode
        return recTypeDict

    def getWaferList(self):
        """Return the wafer list ordered by WaferIndex.

        Each item is ``"File<fid>-#<wafer index>\t<WAFER_ID>"``; the first item is the
        literal ``"-\tStacked Wafer Map"`` entry.
        """
        self.checkConnection()
        return self._fetcher.get_wafer_list()

    def getSiteList(self):
        """Return the set of site numbers found in Dut_Info."""
        self.checkConnection()
        return set(self._fetcher.get_site_list())

    def getHeadList(self):
        """Return the set of head numbers found in Dut_Info."""
        self.checkConnection()
        return set(self._fetcher.get_head_list())

    def getBinInfo(self, isHBIN=True):
        """Return ``{BIN_NUM: {"BIN_NAME": ..., "BIN_PF": ...}}`` for the given bin type.

        Args:
            isHBIN: True for the hardware bin table, False for the software bin table.
        """
        self.checkConnection()
        return self._fetcher.get_bin_info(bool(isHBIN))

    def getBinStats(self, head, site, isHBIN=True):
        """Return ``{BIN_NUM: [count per file]}`` for the DUTs of one head and site.

        Args:
            head: head number.
            site: site number, or -1 for every site.
            isHBIN: True for hardware bins, False for software bins.

        Files without that bin keep a count of 0.
        """
        self.checkConnection()
        BinStats = {}
        for fid, bin_num, count in self._fetcher.get_bin_stats_rows(head, site, isHBIN):
            countList = BinStats.setdefault(bin_num, [0 for _ in range(self.num_files)])
            countList[fid] = count
        return BinStats

    def getFileInfo(self):
        """Return ``{Field: (value per file, ...)}`` from the File_Info table.

        Per file, a field maps to None when unset, to the value itself when it occurs
        once, and otherwise to:
            * "SETUP_T", "START_T", "FINISH_T", "SBLOT_ID": every occurrence joined by
              newlines as ``"#1 → v1\n#2 → v2"``;
            * any other field: only the first occurrence.
        """
        self.checkConnection()
        rows = self._fetcher.get_file_info_rows()
        InfoDict = {}
        for Fid, Field, Value in rows:
            valueList = InfoDict.setdefault(Field, [[] for _ in range(self.num_files)])
            valueList[Fid].append(Value)

        # convert dict value to tuple of strings
        def process(key, old_value: list) -> tuple:
            new = []
            for info_per_file in old_value:
                # info_per_file contains same field value from all merged files
                if len(info_per_file) == 1:
                    new.append(info_per_file[0])
                elif len(info_per_file) == 0:
                    new.append(None)
                else:
                    if key in ["SETUP_T", "START_T", "FINISH_T", "SBLOT_ID"]:
                        # concat these field values by "\n"
                        new.append("\n".join([f"#{i+1} → {v}" for i, v in enumerate(info_per_file)]))
                    else:
                        # for other fields, only extract info from 1st file
                        new.append(info_per_file[0])
            return tuple(new)

        for key in InfoDict.keys():
            old_value = InfoDict[key]
            InfoDict[key] = process(key, old_value)
        return InfoDict

    def getTestFailCnt(self) -> dict:
        """Return ``{(TEST_NUM, TEST_NAME): [FailCount per file]}``.

        A file without a Test_Info row for that test keeps a count of 0; -1 means
        the file carries no TSR fail count for that test.
        """
        self.checkConnection()
        return self._fetcher.get_test_fail_cnt()

    def getTestInfo(self, testTup, fileId):
        """Return the Test_Info row of one test as a dict, or {} when the file has no such
        (test number, test name).
        """
        self.checkConnection()
        info = self._fetcher.get_test_info(testTup[0], testTup[1], fileId)
        return info if info is not None else {}

    def getTestDataFromHeadSite(self, testTup, heads, sites, fileId):
        """Return the test data of the non-superseded DUTs of the given heads and sites.

        The keys depend on the record type:
            PTR: ``dutList``, ``dataList``, ``flagList``
            MPR: ``dutList``, ``dataList``, ``stateList``, ``flagList``
            FTR: ``dutList``, ``flagList``

        Args:
            testTup: (TEST_NUM, TEST_NAME).
            heads: selected head numbers.
            sites: selected site numbers; -1 selects every site.
            fileId: file id.

        Returns {} when the file has no such test.
        """
        self.checkConnection()
        return self._fetcher.get_test_data_from_head_site(
            testTup[0], testTup[1], list(heads), list(sites), fileId
        )

    def getTestDataFromDutIndex(self, testTup, duts, fileId):
        """Return the test data of the requested DUT indices (1-based).

        Unlike `getTestDataFromHeadSite` this includes superseded DUTs, and the result
        always has one entry per requested DUT (sorted ascending, duplicates kept):
        DUTs without data, or out of range, keep the defaults (NaN / 0xF / -1) and the
        requested length is preserved. The keys are the same as
        `getTestDataFromHeadSite`.

        Returns {} when ``duts`` is empty or the file has no such test.
        """
        self.checkConnection()
        # `duts` is passed through as-is (list or uint64 ndarray): pyo3 extracts
        # it directly, so there is no Python-side element-by-element loop.
        return self._fetcher.get_test_data_from_dut_index(
            testTup[0], testTup[1], duts, fileId
        )

    def getDUTCountDict(self) -> dict:
        """Return ``{"Total"|"Pass"|"Failed"|"Unknown"|"Superseded": [count per file]}``."""
        self.checkConnection()
        return self._fetcher.get_dut_count_dict()

    def getDUTCountOnConditions(self, head: int, site: int, waferid: int, fid: int):
        """Return ``[Pass, Failed, Unknown, Superseded]`` counts for the given filters.

        Args:
            head: head number, or -1 for any head.
            site: site number, or -1 for any site.
            waferid: wafer index, or -1 for any wafer.
            fid: file id, or -1 for any file.
        """
        self.checkConnection()
        return self._fetcher.get_dut_count_on_conditions(head, site, waferid, fid)

    def getDutIndexDictFromHeadSite(self, heads: list[int], sites: list[int], fileIds: list[int]) -> dict:
        """Return ``{fid: uint64 ndarray of DUTIndex}`` matching the heads and sites.

        Files without a matching DUT are omitted, and an empty heads/sites selection
        returns {}. ``sites`` containing -1 selects every site; superseded DUTs are
        included.
        """
        self.checkConnection()
        return self._fetcher.get_dut_index_dict_by_head_site(
            list(heads), list(sites), list(fileIds)
        )

    def getDUTIndexFromBin(self, selectedBin: list) -> list:
        """Return the unique ``(fid, DUTIndex)`` pairs matching the given bins.

        Args:
            selectedBin: a list of ``(fid, isHBIN, [bin number])`` selections.
        """
        self.checkConnection()
        selections = [(fid, bool(isHBIN), list(binList)) for fid, isHBIN, binList in selectedBin]
        return self._fetcher.get_dut_index_rows_by_bin(selections)

    def getDUTIndexFromXY(self, selectedDie: list) -> list:
        """Return the ``(fid, DUTIndex)`` pairs matching the given die coordinates.

        Args:
            selectedDie: a list of ``(waferInd, fid, (x, y))`` selections; a
                ``waferInd`` of -1 searches the stacked map across all files.
        """
        self.checkConnection()
        selections = [(waferInd, fid, (int(x), int(y))) for waferInd, fid, (x, y) in selectedDie]
        return self._fetcher.get_dut_index_rows_by_xy(selections)

    def getWaferBounds(self, waferIndex: int, fid: int) -> tuple:
        """Return ``(xmax, xmin, ymax, ymin)`` of the given wafer.

        Args:
            waferIndex: wafer index, or -1 for the stacked map.
            fid: file id (ignored for the stacked map).

        An entry is None when no DUT of the wafer has coordinates.
        """
        self.checkConnection()
        return self._fetcher.get_wafer_bounds(waferIndex, fid)

    def getDynamicLimits(self, test_num: int, test_name: str, dutList, fileId: int):
        """Return ``(low limits, high limits)`` as float32 arrays, one entry per requested
        DUT in the order of ``dutList``.

        A requested DUT gets its dynamic limit when one exists, otherwise the static
        default from Test_Info. A side is an empty array when none of the requested
        DUTs has a dynamic limit for that side, in which case the caller falls back to
        the static limit.
        """
        self.checkConnection()
        return self._fetcher.get_dynamic_limits(
            int(fileId), int(test_num), test_name, dutList
        )

    def getPartialDUTInfoOnCondition(self, heads: list[int], sites: list[int], fileId: int) -> dict:
        """Return ``{DUTIndex: (PartID, PartText, "Head h - Site s", "State - 0xFL")}``.

        Args:
            heads: selected head numbers.
            sites: selected site numbers; -1 selects every site.
            fileId: file id.

        Superseded DUTs are included. Returns {} when either selection is empty.
        """
        self.checkConnection()
        if len(heads) == 0 or len(sites) == 0:
            return {}
        return self._fetcher.get_partial_dut_info(list(heads), list(sites), int(fileId))

    def getFullDUTInfoFromDutArray(self, dutArray: np.ndarray, fid: int) -> dict:
        """Return ``{DUTIndex: [File ID, Part ID, Part Text, head-site, tests executed,
        test time, HBIN, SBIN, wafer id, (X, Y), DUT flag]}``.

        Every DUT of ``dutArray`` gets an entry; a DUT without a matching Dut_Info row
        maps to an empty tuple ``()``.
        """
        self.checkConnection()
        return self._fetcher.get_full_dut_info(dutArray, int(fid))

    def getPinNames(self, testNum: int, testName: str, isRTN=True):
        """Return the pin map of one MPR or FTR test, per file.

        The result is::

            {
                "PMR":      [[pmr index, ...] per file],
                "LOG_NAM":  [[logical name, ...] per file],
                "PHY_NAM":  [[physical name, ...] per file],
                "CHAN_NAM": [{(head, site): [channel name, ...]} per file],
            }

        PMR order is preserved, and channel names are grouped by head/site because they
        can differ between sites.

        Args:
            testNum: test number.
            testName: test name.
            isRTN: True for the RTN pin map, False for the PGM pin map.
        """
        self.checkConnection()
        pinNameDict = {"PMR": [], "LOG_NAM": [], "PHY_NAM": [], "CHAN_NAM": []}
        for fid in range(self.num_files):
            rows = self._fetcher.get_pin_name_rows(int(testNum), testName, bool(isRTN), fid)
            tmpPMR = []
            tmpLOG = []
            tmpPHY = []
            tmpCHAN = {}
            for pmr_index, log_nam, phy_nam, head_num, site_num, chan_nam in rows:
                # keep original PMR order; channel name is head-site dependent
                if pmr_index not in tmpPMR:
                    tmpPMR.append(pmr_index)
                    tmpLOG.append(log_nam)
                    tmpPHY.append(phy_nam)
                tmpCHAN.setdefault((head_num, site_num), []).append(chan_nam)
            pinNameDict["PMR"].append(tmpPMR)
            pinNameDict["LOG_NAM"].append(tmpLOG)
            pinNameDict["PHY_NAM"].append(tmpPHY)
            pinNameDict["CHAN_NAM"].append(tmpCHAN)
        return pinNameDict

    def getWaferInfo(self):
        """Return ``{(WaferIndex, Fid): {column: value}}`` from the Wafer_Info table.

        Missing cells become "N/A". Wafer xy direction and die ratio fields read from
        File_Info are merged into every entry of the same file.
        """
        self.checkConnection()
        col = ["Fid", "HEAD_NUM", "WaferIndex", "PART_CNT", "RTST_CNT", "ABRT_CNT",
               "GOOD_CNT", "FUNC_CNT", "WAFER_ID", "FABWF_ID", "FRAME_ID",
               "MASK_ID", "USR_DESC", "EXC_DESC"]
        waferDict = {}
        for row in self._fetcher.get_wafer_info_rows():
            fid = row[0]
            waferIndex = row[2]
            valueList = ["N/A" if ele is None else ele for ele in row]
            waferDict[(waferIndex, fid)] = dict(zip(col, valueList))
        # wafer xy direction and die ratio come from File_Info
        for fid in range(self.num_files):
            ext_info = {}
            for field, value in self._fetcher.get_wafer_ext_rows(fid):
                if value is None or value in ["", " "]:
                    pass
                else:
                    ext_info[field] = value
            for k, v in waferDict.items():
                if k[-1] == fid:
                    v.update(ext_info)
        return waferDict

    def getWaferCoordsDict(self, waferIndex, sites, fid):
        """Return ``{SBIN: {"x": ndarray, "y": ndarray}}`` for one wafer.

        Args:
            waferIndex: wafer index.
            sites: selected site numbers; -1 selects every site.
            fid: file id.

        DUTs without coordinates are skipped.
        """
        self.checkConnection()
        rows = self._fetcher.get_wafer_coord_rows(int(waferIndex), list(sites), int(fid))
        coordsDict = {}
        for sbin, x, y in rows:
            nested = coordsDict.setdefault(sbin, {})
            nested.setdefault("x", []).append(x)
            nested.setdefault("y", []).append(y)
        for nested in coordsDict.values():
            nested["x"] = np.array(nested["x"])
            nested["y"] = np.array(nested["y"])
        return coordsDict

    def getStackedWaferData(self, sites):
        """Return ``{fail count: {"x": ndarray, "y": ndarray}}`` over all files.

        Coordinates are grouped by (X, Y) and the counts of failing DUTs (Flag & 24 == 8)
        are summed per coordinate; ``sites`` of -1 selects every site.
        """
        self.checkConnection()
        rows = self._fetcher.get_stacked_wafer_rows(list(sites))
        failDieDistribution = {}
        for x, y, flag, count in rows:
            # seed every coordinate (even non-failing ones end up as count 0),
            # exactly like the reference setdefault + add pattern
            previousCount = failDieDistribution.setdefault((x, y), 0)
            if flag & 24 == 8:
                failDieDistribution[(x, y)] = previousCount + count
        failDict = {}
        for (x, y), count in failDieDistribution.items():
            nested = failDict.setdefault(count, {})
            nested.setdefault("x", []).append(x)
            nested.setdefault("y", []).append(y)
        for nested in failDict.values():
            nested["x"] = np.array(nested["x"])
            nested["y"] = np.array(nested["y"])
        return failDict

    def getDTR_GDRs(self):
        """Return the GDR/DTR records as a list of
        ``(Record Type, Value, Approx. Location)`` tuples.
        """
        self.checkConnection()
        return self._fetcher.get_datalog_rows()
