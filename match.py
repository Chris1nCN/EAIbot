#!/usr/bin/env python  
#coding=utf-8

import socket
import rospy
import threading
import time
import os, sys, select, termios, tty
from dobot.srv import SetPTPCommonParams
from dobot.srv import SetQueuedCmdClear
from std_msgs.msg import String
from move_base_msgs.msg import MoveBaseActionResult
from dashgo_tools.msg import check_msgActionResult
from actionlib_msgs.msg import GoalID
from move_base_msgs.msg import MoveBaseActionGoal

operation_keys = ['k','1','2','3','4']

def sleepx(timex):
    time.sleep(1*timex)

def nav_callback(data):
    if data.status.status == 3: 
        goal_name = data.status.goal_id.id.split('_')[0]
        if goal_name == "分拣台1":
            #print('到分拣台点1了' + '\n')
            #print('机械臂去观察点')
            sleepx(2.5)  #一般机械臂的动作我们可以简单地用延时来等待它转动完成
            #print('摄像头识别')
        elif goal_name == "湖南":
            #直接投放,或者识别投递箱,再投放
        else:
            print('普通目标点')
    elif data.status.status == 4:
        print('导航失败了，是否重试')
    else:
        print('导航被取消: ' + str(data.status.status))

def grab(tags):
    print("识别邮件")
    #如果视野内有邮件，判断邮件离摄像头的距离，能不能抓到，能抓直接抓，抓不到就微调靠近一定再抓。  （机械臂臂展是30cm）
    #如果没有，该怎么办，是去下一个点还是怎么做。

def grab_to_release():
    print("投放邮件")
    #投放邮件，直接投放,或者识别投递箱,再投放
    #放完之后，去下一个分拣台点

def grab_tag_to_staging(tag, is_single):
    #抓了邮件放机器身上，放一个还是放两个。
    print("抓了邮件放机器身上")
        
def check_callback(data):
    if data.result.issuccess:
        print("位置微调完成")
        #微调完位置了，直接抓，还是再识别一次再抓。

def init_listener():
    rospy.Subscriber('move_base/result', MoveBaseActionResult, nav_callback)  #订阅导航结果话题数据
    rospy.Subscriber('check_server/result', check_msgActionResult, check_callback) #订阅（微调）走固定距离结果话题数据

def init_publisher():
    global check_pub
    global pause_nav
    global goal_pub
    goal_pub = rospy.Publisher('move_base/goal', MoveBaseActionGoal, queue_size=1)      #目标点发布器
    #目标点里面的goal_id的id与上一次的id不能相同
    check_pub = rospy.Publisher('check', String, queue_size=1)      #微调发布器
    pause_nav = rospy.Publisher('move_base/cancel', GoalID, queue_size=1)       #暂停导航发布器

def initSpeed():
    rospy.wait_for_service('DobotServer/SetPTPCommonParams')
    try:
        client = rospy.ServiceProxy('DobotServer/SetPTPCommonParams',SetPTPCommonParams)
        response = client(200, 200, False)
    except rospy.ServiceException as e:
        print("Service call failed: %s"%e)

def clearQueue():
    rospy.wait_for_service('DobotServer/SetQueuedCmdClear')
    try:
        client = rospy.ServiceProxy('DobotServer/SetQueuedCmdClear',SetQueuedCmdClear)
        response = client()
    except rospy.ServiceException as e:
        print("Service call failed: %s"%e)

def getTargets():
    #目标点的文件目录要写完整
    with open('xxxxx.target','r') as f:
        text = f.read().splitlines()
        for i in text:
            print("可以存到数组里面")

def main():
    getTargets()    #加载目标点。根据你的逻辑，去读取目标点文件，加载需要的目标点
    init_listener()  #注册导航点的监听
    init_publisher() #注册移动固定距离/角度的发布器
    initSpeed()     #修改机械臂速度
    clearQueue()    #清除所有机械臂动作

    #print('气泵停止抽气')
    #发送去第一个分拣台点

def getKey():
    tty.setraw(sys.stdin.fileno())
    select.select([sys.stdin], [], [], 0)
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

def thread_job():
    main()

def init_key_listener():
    global settings
    settings = termios.tcgetattr(sys.stdin)
    try:
        while(1):
            key = getKey()
            if key in operation_keys:
                print(key)
                if key == 'k':
                    print('停止导航,关闭程序')
                    #关闭气泵
                    sleepx(1)
                    os._exit(1) #关闭程序
                if key == '1':
                    print(recvData + '恢复导航\n')
                if key == '2':
                    print('暂停导航')
                    pause_nav.publish(GoalID()) #暂停导航
    except Exception as e:
        print e
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)

if __name__ == "__main__":
    rospy.init_node('match_topic', anonymous=True)  #给本程序初始化一个节点名称
    main_thread = threading.Thread(target = thread_job)     #开一个线程处理任务
    main_thread.start()
   
    #写一个键盘监听，可以根据我们的按键做对应的操作，
    #这里主要是为了当我们需要申请救援的时候，可以及时暂停机器的导航/机械臂的运动等等，方便我们立刻将机器带回出发区
    #而程序暂停，所有状态仍然能够保存。  救援完成时，只需要恢复最近一次的导航任务，便可以继续我们的任务。
    key_thread = threading.Thread(target = init_key_listener)   #开一个线程处理键盘监听
    key_thread.start()   
