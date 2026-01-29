/*
 Navicat Premium Data Transfer

 Source Server         : CodeRecognition
 Source Server Type    : MySQL
 Source Server Version : 80036
 Source Host           : localhost:3306
 Source Schema         : code_user_db

 Target Server Type    : MySQL
 Target Server Version : 80036
 File Encoding         : 65001

 Date: 29/01/2026 15:34:38
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for code_captcha
-- ----------------------------
DROP TABLE IF EXISTS `code_captcha`;
CREATE TABLE `code_captcha`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键',
  `captcha_img_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '验证码图片文件名',
  `captcha_img_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '验证码图片本地绝对路径',
  `correct_code` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '正确验证码（图片名前4位）',
  `create_time` datetime NOT NULL COMMENT '导入时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `captcha_img_path`(`captcha_img_path`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 102 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '验证码图片信息表（图片名前4位为正确码）' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for code_user
-- ----------------------------
DROP TABLE IF EXISTS `code_user`;
CREATE TABLE `code_user`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '登录账号',
  `password` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '加密后的密码',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `username`(`username`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '验证码系统登录用户表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for code_user_operation
-- ----------------------------
DROP TABLE IF EXISTS `code_user_operation`;
CREATE TABLE `code_user_operation`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `account` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户账号',
  `password` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '加密后的密码',
  `verification_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '验证码',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户操作表（code前缀）' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for code_verify_log
-- ----------------------------
DROP TABLE IF EXISTS `code_verify_log`;
CREATE TABLE `code_verify_log`  (
  `log_id` int NOT NULL AUTO_INCREMENT COMMENT '日志唯一ID',
  `captcha_id` int NOT NULL COMMENT '关联的验证码ID',
  `input_captcha` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户输入的验证码',
  `correct_captcha` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '数据库正确验证码',
  `is_match` tinyint(1) NOT NULL COMMENT '是否匹配：1=是，0=否',
  `verify_user` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '验证账号',
  `verify_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '验证时间',
  PRIMARY KEY (`log_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '验证码验证系统日志表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
