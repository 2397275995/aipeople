# Live2D Cubism SDK 集成说明

本目录用于放置 **Live2D Cubism SDK for Web** 与模型资源。项目不包含 SDK 本体，需自行下载。

## 1. 下载 SDK

1. 前往 [Live2D Cubism SDK 下载页](https://www.live2d.com/download/cubism-sdk/download-web/)
2. 下载 **Cubism SDK for Web** 并解压

## 2. 复制 Core 库

将 Core 文件复制到：

```
public/live2dcubismcore/live2dcubismcore.min.js
```

## 3. 桥接脚本

将官方 Sample 构建产物复制为 `public/live2d/sdk/live2d-app.js`，需暴露 `window.Live2DApp.init()`。

开发阶段可临时将 `live2d-app.stub.js` 复制为 `live2d-app.js` 验证口型与音频链路。

## 4. 放置模型

```
public/live2d/models/Hiyori/Hiyori.model3.json
```

## 5. 口型参数

默认驱动 `ParamMouthOpenY`，时间戳来自后端 TTS `phonemes` 字段。
