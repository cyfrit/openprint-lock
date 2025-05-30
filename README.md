# OpenPrint Lock
## 简介
OpenPrint Lock 是一个开源的指纹锁，理论上可以运行在任何支持 MicroPython 的设备上。  
指纹传感器支持海凌科ZW系列。  
使用 ESP32C3，海凌科 ZW111 指纹传感器，SG90 180度舵机，成本不到30元。  
## 关于舵机
考虑到不同门适用的开锁方式不同，需要自行设计舵机的开锁方式。  
本项目提供的舵机开锁方式可以控制舵机的起始角度与结束角度，这适用于我使用的老式门锁，只需要用舵机用线拉一下就可以打开。  
## 硬件要求
尽管只需要支持 MicroPython 即可，但需要一个 UART 接口来连接指纹传感器，和至少一个 GPIO 接口来连接舵机。此外，还需要2个3V3供电接口(指纹传感器)和1个5v供电接口(舵机)。（应该不会有板子只有一个GND吧）。  
为了连接指纹传感器，还需要一根 SH1.0 转杜邦 6P 线，买指纹模块的时候可以一起买。  
以及用于连接舵机的杜邦线。  
## 安装
### 硬件
按照海凌科提供的定义进行连接。注意，ZW系列不同型号的引脚顺序是不同的。  
模块的TX连接开发版的RX，RX连接开发版的TX。
### 固件
将 config.example.py 重命名为 config.py，并根据需要修改配置。  
根据各个开发版的指南，刷入 MicroPython 固件。  
如果没有使用过 MicroPython, 推荐使用 Thonny 刷入代码。  
电脑连接开发版，选择开发版串口，将代码上传到 MicroPython 中。  
重启开发版，去路由器看看开发版的 IP 地址，然后 curl 一下看看是否正常。
## 使用
已经部署了现成的，[OpenPrint Lock](http://openprint-lock.cli.tf/)，可以直接使用。  
由于浏览器限制，如果后端没有https，前端也需要使用http协议。  
在前端的系统设置中配置连接信息。  
如果需要自行部署开发前端:  
开发服务器  
```bash
pnpm run dev
```
构建生产  
```bash
pnpm run build
```
## 注意 
本项目仅用于研究和学习。强烈建议不要将此项目作为真正的门禁，使用本项目，即表示您愿意自行承担因使用本项目所产生的风险与损失。
