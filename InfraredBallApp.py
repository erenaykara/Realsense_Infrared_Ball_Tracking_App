# -*- coding: utf-8 -*-

import sys
import os
import cv2
import datetime
import numpy as np
import json

from Implement.RealsenseVideoCapture import RealsenseVideoCapture

from UI.InfraredBall import Ui_MainWindow
# from UI.Init import Ui_Init

from PyQt5.QtWidgets import *


# class InitApp(QMainWindow, Ui_Init):
#     def __init__(self):
#         super(InitApp, self).__init__()
#         self.setupUi(self)
#         self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
#
#     def realsense_init(self):
#         realsense_video_capture = RealsenseVideoCapture()
#         return realsense_video_capture


class InfraredBallApp(QMainWindow, Ui_MainWindow):
    def __init__(self, vidcap):
        super(InfraredBallApp, self).__init__(vid_cap=vidcap)
        self.setupUi(self)

        self.pushButton_5.setEnabled(False)
        self.pushButton_6.setEnabled(False)
        self.save_file_dir = {}

        self.filedir = self.first_time_config()

        # videoConfig
        self.fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # detect_config
        self.camera_cap.detect_left_threshold = self.lineEdit_2.text()
        self.camera_cap.detect_right_threshold = self.lineEdit.text()

    def start_up_camera_and_detect_infrared_ball(self):
        print("打开相机并检测小球")
        self.pushButton.setEnabled(False)
        self.pushButton_5.setEnabled(True)
        self.label_7.clear()
        if self.camera_cap.isOpened():
            self.Timer.start(30)

        # 展示数据
        self.infrared_ball_display()

    def start_record(self):
        """start record"""
        self.pushButton_5.setEnabled(False)
        self.pushButton_6.setEnabled(True)
        self.record_ball_number = self.pointNum

        if self.record_ball_number == 0:
            message_box = QMessageBox()
            message_box.setWindowTitle("红外反光球动作捕捉系统")
            message_box.setText("请确保检测到小球时再点击录制")
            message_box.setIcon(QMessageBox.Information)
            message_box.setStandardButtons(QMessageBox.Ok)
            result = message_box.exec_()
            if result == QMessageBox.Ok:
                self.pushButton_5.setEnabled(True)
                self.pushButton_6.setEnabled(False)
        else:
            if self.out is None:
                self.out = self.video_record_config()

    def end_record(self):
        """end record"""

        """release resources"""
        self.out.release()

        np.savez(os.path.join(self.save_dir, "Trajectory.npz"),
                 joint_2d=np.array(self.Sequence2D),
                 joint_3d=np.array(self.Sequence3D))

        self.record_ball_number = 0

        self.out = None

        self.Sequence3D = []
        self.Sequence2D = []

        message_box = QMessageBox()
        message_box.setWindowTitle("红外反光球动作捕捉系统")
        message_box.setText("录制完成，结果保存至" + self.save_dir)
        message_box.setIcon(QMessageBox.Information)
        message_box.setStandardButtons(QMessageBox.Ok)
        result = message_box.exec_()
        if result == QMessageBox.Ok:
            self.pushButton_5.setEnabled(True)
            self.pushButton_6.setEnabled(False)

    def first_time_config(self):
        """first configuration"""
        if not os.path.exists("./cache.json"):
            default_path = "C:\\"
            filedir = QFileDialog.getExistingDirectory(None, "首次使用请选取保存的文件夹", default_path)
            self.save_file_dir['file_path'] = filedir
            with open("./cache.json", mode="w") as save_first:
                json.dump(self.save_file_dir, save_first)
        else:
            with open("./cache.json") as cache_f:
                config = json.load(cache_f)
                filedir = config["file_path"]
        return filedir

    def config_save_file_path(self):
        """config file save path"""
        default_path = "C:\\"
        if os.path.exists("./cache.json"):
            with open("./cache.json") as ff:
                default_path = json.load(ff)['file_path']

        filedir = QFileDialog.getExistingDirectory(None, "请选取保存的文件夹", default_path)
        self.save_file_dir['file_path'] = filedir
        with open("./cache.json", mode="w") as save_f:
            json.dump(self.save_file_dir, save_f)
        self.filedir = filedir

    def video_record_config(self):
        self.record_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.save_dir = os.path.join(self.filedir, self.record_time)
        os.makedirs(self.save_dir)
        self.save_path = os.path.join(self.save_dir, "rgb.mp4")
        return cv2.VideoWriter(self.save_path, self.fourcc, 30.0, (640, 480))

    def detect_config(self):
        self.camera_cap.detect_left_threshold = self.lineEdit_2.text()
        self.camera_cap.detect_right_threshold = self.lineEdit.text()

    def quitApp(self):
        message_box = QMessageBox()
        message_box.setWindowTitle("红外反光球动作捕捉系统")
        message_box.setText("确认退出吗？")
        message_box.setIcon(QMessageBox.Information)
        message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        result = message_box.exec_()
        if result == QMessageBox.Ok:
            sys.exit(0)
        elif result == QMessageBox.Cancel:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    vidcap = RealsenseVideoCapture()
    w = InfraredBallApp(vidcap)
    w.show()

    sys.exit(app.exec_())
