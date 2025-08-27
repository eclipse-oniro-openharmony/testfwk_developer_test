#!/usr/bin/env python3
# coding=utf-8

#
# Copyright (c) 2022 Huawei Device Co., Ltd.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import copy
import json
import sys
from json import JSONDecodeError
from core.utils import get_build_output_path
from core.common import is_open_source_product

from core.utils import get_file_list_by_postfix
from core.config.config_manager import FilterConfigManager
from xdevice import platform_logger
from xdevice import DeviceTestType
from xdevice import Binder

LOG = platform_logger("TestcaseManager")

TESTFILE_TYPE_DATA_DIC = {
    "DEX": [],
    "HAP": [],
    "PYT": [],
    "CXX": [],
    "BIN": [],
    "OHJST": [],
    "JST": [],
    "LTPPosix": [],
    "OHRust": [],
    "ABC": []
}
FILTER_SUFFIX_NAME_LIST = [".TOC", ".info", ".pyc"]


class TestCaseManager(object):
    @classmethod
    def get_valid_suite_file(cls, test_case_out_path, suite_file, options):
        partlist = options.partname_list
        testmodule = options.testmodule
        testsuit = options.testsuit

        if not suite_file.startswith(test_case_out_path):
            return False

        if testsuit != "":
            short_name, _ = os.path.splitext(os.path.basename(suite_file))
            testsuit_list = testsuit.split(',')
            for test in testsuit_list:
                if short_name == test:
                    return True
            return False

        is_valid_status = False
        suitfile_subpath = suite_file.replace(test_case_out_path, "")
        suitfile_subpath = suitfile_subpath.strip(os.sep)
        if len(partlist) == 0:
            if testmodule != "":
                is_valid_status = False
            else:
                is_valid_status = True
        else:
            for partname in partlist:
                if testmodule != "":
                    module_list = testmodule.split(",")
                    for module in module_list:
                        if suitfile_subpath.startswith(
                            partname + os.sep + module + os.sep):
                            is_valid_status = True
                            break
                else:
                    if suitfile_subpath.startswith(partname + os.sep):
                        is_valid_status = True
                        break
        return is_valid_status

    @classmethod
    def check_python_test_file(cls, suite_file):
        if suite_file.endswith(".py"):
            filename = os.path.basename(suite_file)
            if filename.startswith("test_"):
                return True
        return False

    @classmethod
    def check_hap_test_file(cls, hap_file_path):
        try:
            if hap_file_path.endswith(".hap"):
                json_file_path = hap_file_path.replace(".hap", ".json")
                if os.path.exists(json_file_path):
                    with open(json_file_path, 'r') as json_file:
                        data_dic = json.load(json_file)
                        if not data_dic:
                            return False
                        else:
                            if "kits" in data_dic.keys():
                                kits_list = data_dic.get("kits")
                                if len(kits_list) > 0:
                                    for kits_dict in kits_list:
                                        if "test-file-name" not in kits_dict.keys():
                                            continue
                                        else:
                                            return True
                                else:
                                    return False
            return False
        except JSONDecodeError:
            return False
        finally:
            print(" check hap test file finally")

    @classmethod
    def get_hap_test_driver(cls, hap_file_path):
        data_dic = cls.get_hap_json(hap_file_path)
        if not data_dic:
            return ""
        else:
            if "driver" in data_dic.keys():
                driver_dict = data_dic.get("driver")
                if bool(driver_dict):
                    driver_type = driver_dict.get("type")
                    return driver_type
                else:
                    LOG.error("%s has not set driver." % hap_file_path)
                    return ""
            else:
                return ""

    @classmethod
    def get_hap_json(cls, hap_file_path):
        if hap_file_path.endswith(".hap"):
            json_file_path = hap_file_path.replace(".hap", ".json")
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as json_file:
                    data_dic = json.load(json_file)
                    return data_dic
            else:
                return {}
        else:
            return {}

    @classmethod
    def get_hap_part_json(cls, hap_file_path):
        if hap_file_path.endswith(".hap"):
            json_file_path = hap_file_path.replace(".hap", ".moduleInfo")
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as json_file:
                    data_dic = json.load(json_file)
                    return data_dic
            else:
                return {}
        else:
            return {}

    @classmethod
    def get_part_name_test_file(cls, hap_file_path):
        data_dic = cls.get_hap_part_json(hap_file_path)
        if not data_dic:
            return ""
        else:
            if "part" in data_dic.keys():
                part_name = data_dic["part"]
                return part_name
            else:
                return ""
    
    def get_test_files(self, test_case_path, options):
        LOG.info("test case path: " + test_case_path)
        LOG.info("test type list: " + str(options.testtype))
        suit_file_dic = copy.deepcopy(TESTFILE_TYPE_DATA_DIC)
        if os.path.exists(test_case_path):
            if len(options.testtype) != 0:
                test_type_list = options.testtype
                suit_file_dic = self.get_test_file_data(
                    test_case_path,
                    test_type_list,
                    options)
        else:
            LOG.error("%s is not exist." % test_case_path)
        return suit_file_dic

    def get_test_file_data(self, test_case_path, test_type_list, options):
        suit_file_dic = copy.deepcopy(TESTFILE_TYPE_DATA_DIC)
        for test_type in test_type_list:
            temp_dic = self.get_test_file_data_by_test_type(
                test_case_path,
                test_type,
                options)
            for key, value in suit_file_dic.items():
                suit_file_dic[key] = value + temp_dic.get(key)
        return suit_file_dic

    def get_test_file_data_by_test_type(self, test_case_path,
                                        test_type, options):
        suit_file_dictionary = copy.deepcopy(TESTFILE_TYPE_DATA_DIC)
        test_case_out_path = os.path.join(test_case_path, test_type)
        if os.path.exists(test_case_out_path):
            LOG.info("The test case directory: %s" % test_case_out_path)
            return self.get_all_test_file(test_case_out_path, options)
        else:
            LOG.error("Test case dir does not exist. %s" % test_case_out_path)
        return suit_file_dictionary

    def get_all_test_file(self, test_case_out_path, options):
        suite_file_dictionary = copy.deepcopy(TESTFILE_TYPE_DATA_DIC)
        filter_part_list = FilterConfigManager().get_filtering_list(
            "subsystem_name", options.productform)
        filter_list_test_file = FilterConfigManager().get_filtering_list(
            "testfile_name", options.productform)
        # 遍历测试用例输出目录下面的所有文件夹，每个文件夹对应一个子系统
        command_list = options.current_raw_cmd.split(" ")
        for part_name in os.listdir(test_case_out_path):
            if "-ss" in command_list or "-tp" in command_list:
                if part_name not in options.partname_list:
                    continue
            part_case_dir = os.path.join(test_case_out_path, part_name)
            if not os.path.isdir(part_case_dir):
                continue
            # 如果子系统在fiter_config.xml配置文件的<subsystem_name>下面配置过，则过滤
            if part_name in filter_part_list:
                continue

            # 获取子系统目录下面的所有文件路径列表
            suite_file_list = get_file_list_by_postfix(part_case_dir)
            for suite_file in suite_file_list:
                # 如果文件在resource目录下面，需要过滤
                if -1 != suite_file.replace(test_case_out_path, "").find(
                        os.sep + "resource" + os.sep):
                    continue

                file_name = os.path.basename(suite_file)
                # 如果文件在fiter_config.xml配置文件的<testfile_name>下面配置过，则过滤
                if file_name in filter_list_test_file:
                    continue

                prefix_name, suffix_name = os.path.splitext(file_name)
                if suffix_name in FILTER_SUFFIX_NAME_LIST:
                    continue

                if not self.get_valid_suite_file(test_case_out_path,
                                                suite_file,
                                                options):
                    continue

                if suffix_name == ".dex":
                    suite_file_dictionary.get("DEX").append(suite_file)
                elif suffix_name == ".hap":
                    if self.get_hap_test_driver(suite_file) == "OHJSUnitTest":
                        # 如果stage测试指定了-tp，只有部件名与moduleInfo中part一致的HAP包才会加入最终执行的队列
                        if options.testpart != [] and options.testpart[0] != self.get_part_name_test_file(
                                suite_file):
                            continue
                        # 如果stage测试指定了-ts，只有完全匹配的HAP包才会加入最终执行的队列
                        if options.testsuit != "":
                            testsuit_list = options.testsuit.split(";")
                            is_match = False
                            for suite_item in testsuit_list:
                                if suite_item == prefix_name:
                                    is_match = True
                                    break
                            if not is_match:
                                continue
                        if not self.check_hap_test_file(suite_file):
                            continue
                        suite_file_dictionary.get("OHJST").append(suite_file)
                    if self.get_hap_test_driver(suite_file) == "JSUnitTest":
                        suite_file_dictionary.get("JST").append(suite_file)
                elif suffix_name == ".py":
                    if not self.check_python_test_file(suite_file):
                        continue
                    suite_file_dictionary.get("PYT").append(suite_file)
                elif suffix_name == "":
                    if file_name.startswith("rust_"):
                        Binder.get_tdd_config().update_test_type_in_source(
                            "OHRust", DeviceTestType.oh_rust_test)
                        suite_file_dictionary.get("OHRust").append(suite_file)
                    else:
                        suite_file_dictionary.get("CXX").append(suite_file)
                elif suffix_name == ".bin":
                    suite_file_dictionary.get("BIN").append(suite_file)
                # 将arktstdd的测试文件加入测试文件字典
                elif (suffix_name == ".abc" and not os.path.dirname(suite_file).endswith("out")
                    and not os.path.dirname(suite_file).endswith("hypium")):
                    suite_file_dictionary.get("ABC").append(suite_file)

        return suite_file_dictionary

    def get_part_deps_files(self, external_deps_path, testpart):
        LOG.info("external_deps_path:" + external_deps_path)
        if os.path.exists(external_deps_path):
            with open(external_deps_path, 'r') as json_file:
                data_dic = json.load(json_file)
                if not data_dic:
                    LOG.error("data_dic is empty.")
                    return []
                test_part = testpart[0]
                if test_part in data_dic.keys():
                    external_deps_part_list = data_dic.get(test_part)
                    LOG.info("external_deps_part_list = %s" % external_deps_part_list)
                    return external_deps_part_list
                else:
                    LOG.error("%s is not in part deps info json." % test_part)
        else:
            LOG.error("Part deps info %s is not exist." % external_deps_path)
        return []
        
    def check_xts_config_match(self, options, prefix_name, xts_suite_file):
        # 如果xts测试指定了-tp，只有部件名与moduleInfo中part一致的文件才会加入最终执行的队列
        if options.testpart != [] and options.testpart[0] != self.get_part_name_test_file(xts_suite_file):
            return False
        # 如果xts测试指定了-ts，只有完全匹配的文件才会加入最终执行的队列
        if options.testsuit != "":
            testsuit_list = options.testsuit.split(";")
            for suite_item in testsuit_list:
                if suite_item == prefix_name:
                    return True
            return False
        return True

    def get_xts_test_files(self, xts_test_case_path, options):
        LOG.info("xts test case path: " + xts_test_case_path)
        xts_suit_file_dic = copy.deepcopy(TESTFILE_TYPE_DATA_DIC)
        if not os.path.exists(xts_test_case_path):
            LOG.error("xts %s is not exist." % xts_test_case_path)
            return xts_suit_file_dic
        # 获取XTS测试用例输出目录下面的所有文件路径列表
        xts_suite_file_list = get_file_list_by_postfix(xts_test_case_path)
        for xts_suite_file in xts_suite_file_list:
            file_name = os.path.basename(xts_suite_file)
            prefix_name, suffix_name = os.path.splitext(file_name)
            if not self.check_xts_config_match(options, prefix_name, xts_suite_file):
                continue
            if suffix_name == "":
                if file_name == "HatsOpenPosixTest":
                    xts_suit_file_dic.get("LTPPosix").append(xts_suite_file)
                else:
                    xts_suit_file_dic.get("CXX").append(xts_suite_file)
            elif suffix_name == ".hap":
                if self.get_hap_test_driver(xts_suite_file) == "OHJSUnitTest":
                    xts_suit_file_dic.get("OHJST").append(xts_suite_file)
                if self.get_hap_test_driver(xts_suite_file) == "JSUnitTest":
                    xts_suit_file_dic.get("JST").append(xts_suite_file)
        return xts_suit_file_dic
