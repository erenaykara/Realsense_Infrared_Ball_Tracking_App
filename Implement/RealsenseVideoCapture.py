import sys

import cv2
import pyrealsense2 as rs
import imutils
from imutils import contours
from skimage import measure

from camera_parameters import *
from Convert import estimateDepth, project_point, getPointXYZ

from PyQt5.QtWidgets import *


class RealsenseVideoCapture(object):
    def __init__(self):
        super(RealsenseVideoCapture, self).__init__()

        self.detect_left_threshold = 50
        self.detect_right_threshold = 250
        # 40, 300

        if self.isOpened():
            self.pipeline = rs.pipeline()
            config = rs.config()

            config.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, 30)  # infrared stream
            config.enable_stream(rs.stream.infrared, 2, 640, 480, rs.format.y8, 30)  # infrared stream
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)  # rgb stream

            pipe_profile = self.pipeline.start(config)

            align_to = rs.stream.color
            self.align = rs.align(align_to)

            message_box = QMessageBox()
            message_box.setWindowTitle("红外反光球动作捕捉系统")
            message_box.setText("已检测到Realsense连接，请点击 OK 继续使用")
            message_box.setIcon(QMessageBox.Information)
            message_box.setStandardButtons(QMessageBox.Ok)
            message_box.exec_()
        else:
            message_box = QMessageBox()
            message_box.setWindowTitle("红外反光球动作捕捉系统")
            message_box.setText("未检测到Realsense连接，请确认连接后重新启动")
            message_box.setIcon(QMessageBox.Information)
            message_box.setStandardButtons(QMessageBox.Ok)
            result = message_box.exec_()
            if result == QMessageBox.Ok:
                sys.exit(0)

    def isOpened(self):
        ctx = rs.context()
        devices = ctx.query_devices()
        if len(devices) > 0:
            return True
        else:
            return False

    def read(self):
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.align.process(frames)

        aligned_color_frame = aligned_frames.get_color_frame()
        alighed_infr_frame1 = aligned_frames.get_infrared_frame(1)
        alighed_infr_frame2 = aligned_frames.get_infrared_frame(2)

        img_color = np.asanyarray(aligned_color_frame.get_data())
        img_infr1 = np.asanyarray(alighed_infr_frame1.get_data())
        img_infr2 = np.asanyarray(alighed_infr_frame2.get_data())

        return img_color, img_infr1, img_infr2

    def detect_infrared_ball(self):
        img_color, img_infr1, img_infr2 = self.read()
        img_color_source = img_color.copy()

        img1, joints_2d1 = self.detect_single_infrared_frame(img_infr1)
        img2, joints_2d2 = self.detect_single_infrared_frame(img_infr2)

        point2D = []
        point3D = []

        if joints_2d1 is not None and joints_2d2 is not None:
            if len(joints_2d1) == len(joints_2d2):
                color_points = []
                for i in range(len(joints_2d1)):
                    Depth = estimateDepth(joints_2d1[i], joints_2d2[i])

                    if Depth == 0:
                        continue

                    color_point = project_point(joints_2d1[i], intrinsics_infr1, R_infr1_to_color, intrinsics_color, T_infr1_to_color, Depth)
                    color_points.append(color_point)

                    str_detected = "Detected Marker nums is {}".format(len(joints_2d1))
                    cv2.putText(img_color, str_detected, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color=(0, 0, 255))

                    str_show = "Coordinate is (" + str(int(color_point[0])) + ", " + str(int(color_point[1])) + ")"
                    cv2.putText(img_color, str_show, (20, (i + 2) * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color=(0, 0, 255))

                    cv2.circle(img_color, (int(color_point[0]), int(color_point[1])), 5, (0, 0, 255), -1)
                    point3D.append(getPointXYZ(joints_2d1[i][0], joints_2d1[i][1], intrinsics_infr1, Depth))
                    point2D.append([int(color_point[0]), int(color_point[1])])
            else:
                pass
        else:
            pass
        return img_color_source, img_color, img1, img2, point2D, point3D

    def detect_single_infrared_frame(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        thresh = cv2.threshold(image, 250, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.erode(thresh, None, iterations=1)
        thresh = cv2.dilate(thresh, None, iterations=4)

        labels = measure.label(thresh, connectivity=1, background=0)
        mask = np.zeros(thresh.shape, dtype="uint8")
        # loop over the unique components
        for label in np.unique(labels):
            # if this is the background label, ignore it
            if label == 0:
                continue
            labelMask = np.zeros(thresh.shape, dtype="uint8")
            labelMask[labels == label] = 255
            numPixels = cv2.countNonZero(labelMask)
            if int(self.detect_left_threshold) < numPixels < int(self.detect_right_threshold):
                mask = cv2.add(mask, labelMask)

        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        num_detected = len(cnts)
        if num_detected == 0:
            # str_no_detected = "Detected Marker nums is 0"
            # cv2.putText(image_rgb, str_no_detected, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color=(0, 0, 255))
            return image_rgb, None
        else:
            joints_2d = []
            cnts = contours.sort_contours(cnts)[0]
            # loop over the contours
            for (i, c) in enumerate(cnts):
                # (x, y, w, h) = cv2.boundingRect(c)
                ((cX, cY), radius) = cv2.minEnclosingCircle(c)

                str_detected = "Detected Marker nums is {}".format(num_detected)
                cv2.putText(image_rgb, str_detected, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color=(0, 0, 255))

                str_show = "Coordinate is (" + str(int(cX)) + ", " + str(int(cY)) + ")"
                cv2.putText(image_rgb, str_show, (20, (i + 2) * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color=(0, 0, 255))

                cv2.circle(image_rgb, (int(cX), int(cY)), int(radius), (0, 0, 255), -1)

                coord_array = np.array([int(cX), int(cY)])
                joints_2d.append(coord_array)
            return image_rgb, joints_2d
