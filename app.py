###############################################################################
#  Copyright (C) 2024 LiveTalking@lipku https://github.com/lipku/LiveTalking
#  email: lipku@foxmail.com
# 
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################
import time
from datetime import datetime

import requests
# server.py
from flask import Flask, render_template, send_from_directory, request, jsonify, session
from flask_sockets import Sockets
import base64
import json
#import gevent
#from gevent import pywsgi
#from geventwebsocket.handler import WebSocketHandler
import re
import numpy as np
from threading import Thread,Event
#import multiprocessing
import torch.multiprocessing as mp

from aiohttp import web
import aiohttp
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription,RTCIceServer,RTCConfiguration
from aiortc.rtcrtpsender import RTCRtpSender

from database_utils import create_hra_data, get_hra_data_by_user_id, update_hra_data
from webrtc import HumanPlayer
from basereal import BaseReal
from llm import (llm_response, llm_response_radar, llm_response_hra, get_quertions_hra, restore_qa_data,
                 normal_model,normal_model_qa,get_question,update_qa)

import argparse
import random
import shutil
import asyncio
import torch
from typing import Dict
from logger import logger
from aiohttp import web

app = Flask(__name__)
#sockets = Sockets(app)
nerfreals:Dict[int, BaseReal] = {} #sessionid:BaseReal
qa_data: Dict[int, list[str]] = {}
opt = None
model = None
avatar = None


#####webrtc###############################
pcs = set()

def randN(N)->int:
    '''生成长度为 N的随机数 '''
    min = pow(10, N - 1)
    max = pow(10, N)
    return random.randint(min, max - 1)

def build_nerfreal(sessionid:int)->BaseReal:
    opt.sessionid=sessionid
    if opt.model == 'wav2lip':
        from lipreal import LipReal
        nerfreal = LipReal(opt,model,avatar)
    elif opt.model == 'musetalk':
        from musereal import MuseReal
        nerfreal = MuseReal(opt,model,avatar)
    # elif opt.model == 'ernerf':
    #     from nerfreal import NeRFReal
    #     nerfreal = NeRFReal(opt,model,avatar)
    elif opt.model == 'ultralight':
        from lightreal import LightReal
        nerfreal = LightReal(opt,model,avatar)
    return nerfreal

#@app.route('/offer', methods=['POST'])
async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    if len(nerfreals) >= opt.max_session:
        logger.info('reach max session')
        return -1
    sessionid = randN(6) #len(nerfreals)
    logger.info('sessionid=%d',sessionid)
    nerfreals[sessionid] = None
    nerfreal = await asyncio.get_event_loop().run_in_executor(None, build_nerfreal,sessionid)
    nerfreals[sessionid] = nerfreal

    #ice_server = RTCIceServer(urls='stun:stun.l.google.com:19302')
    ice_server = RTCIceServer(urls='stun:stun.miwifi.com:3478')
    pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=[ice_server]))
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
            del nerfreals[sessionid]
        if pc.connectionState == "closed":
            pcs.discard(pc)
            del nerfreals[sessionid]

    player = HumanPlayer(nerfreals[sessionid])
    audio_sender = pc.addTrack(player.audio)
    video_sender = pc.addTrack(player.video)
    capabilities = RTCRtpSender.getCapabilities("video")
    preferences = list(filter(lambda x: x.name == "H264", capabilities.codecs))
    preferences += list(filter(lambda x: x.name == "VP8", capabilities.codecs))
    preferences += list(filter(lambda x: x.name == "rtx", capabilities.codecs))
    transceiver = pc.getTransceivers()[1]
    transceiver.setCodecPreferences(preferences)

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    #return jsonify({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type, "sessionid":sessionid}
        ),
    )
async def hra_t(request):
    params = await request.json()
    user_id=params['user_id']
    text=params['text']
    session=requests.Session
    # print(text)
    # print(user_id)
    demo=get_hra_data_by_user_id(user_id)
    if demo is None:
        await create_hra_data(user_id, text)
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": "已成功添加HRA报告"}
            )
        )
    else:
        await update_hra_data(user_id, text)
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": "已成功更改HRA报告"}
            )
        )
async def speak(msg,nerfreal):
    result = ""
    lastpos = 0
    for i, char in enumerate(msg):
        if char in ",.!;:，。！？：；":
            result = result + msg[lastpos:i + 1]
            lastpos = i + 1
            if len(result) > 10:
                logger.info(result)
                nerfreal.put_msg_txt(result)
                result = ""
    result = result + msg[lastpos:]
    nerfreal.put_msg_txt(result)
async def hraHuman(request):

    params = await request.json()
    user_id = params['user_id']
    str = params["type"]
    sessionid = params.get('sessionid', 0)
    if params.get('interrupt'):
        nerfreals[sessionid].flush_talk()
    if params['type'] == 'interrupt':
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": "ok"}
            ),
        )
    elif params['type'] == 'getHra':
        #res = await asyncio.get_event_loop().run_in_executor(None, get_quertions_hra, user_id)

        res = await get_quertions_hra(user_id)

        #print(res)
        # mm = json.dumps(res["data"])
        #
        # result = re.sub(r'(?<!\d)-(\d)|(\d)-(\d)', replace_hyphen, mm)
        # result = json.loads(result)

        result = res["data"]
        # for item in result:
        #     # 对符号进行处理
        #     item["interpretation"] = await convert_ranges_and_negatives(item["interpretation"])
        # print(result)
        print("hra-speak开始说话前")
        await speak(res["message"], nerfreals[sessionid])
        print("hra-speak开始说话了")


        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": result}
            )
        )
    elif params['type'] == 'chat':
        # print("普通rag问答")
        print("日常问答前")
        res = await asyncio.get_event_loop().run_in_executor(None, normal_model, user_id,
                                                             False, params['text'], [],
                                                             nerfreals[sessionid])
        print("日常问答后")
        # print(res)
        if res["code"] == 0:
            # 数字人读
            mss=convert_ranges_and_negatives(res["data"])
            nerfreals[sessionid].put_msg_txt(mss )
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": 0, "data": res["data"]}
                ),
            )
        else:
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": 500, "data": "获取llm回答失败"}
                ),
            )
    elif params['type'] == 'saveQa':
        qas = params['text']
        print(f"qas: {qas}")
        # qa入库
        await restore_qa_data(user_id, qas, nerfreals[sessionid], sessionid)
        qa = json.loads(qas)
        QA_DATA = []

        # 调用总结接口，对用户的问答信息进行总结并入库，前端不展示
        for item in qa:
            QA_DATA.append(item)
        res = await asyncio.get_event_loop().run_in_executor(None, normal_model_qa,
                                                             user_id, True,
                                                             params['text'], QA_DATA,
                                                             nerfreals[sessionid])
        print(f"res = {res}")
        # 数字人读
        msg = res["data"]
        # msg=msg.replace("-","负")
        #nerfreals[sessionid].put_msg_txt(msg)
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": msg}
            )
        )
    # nerfreals[sessionid].put_msg_txt(res)
async def human(request):
    params = await request.json()
    user_id = params['user_id']
    str=params["type"]
    print(str)
    sessionid = params.get('sessionid', 0)
    print(sessionid)
    if params.get('interrupt'):
        nerfreals[sessionid].flush_talk()
    if params['type'] == 'interrupt':
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": "ok"}
            ),
        )
    elif params['type'] == 'echo':
        nerfreals[sessionid].put_msg_txt(params['text'])
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": "ok"}
            ),
        )
    elif params['type'] == 'read':
        msg = params['text']
        # print("np_read:"+msg)
        # print(f"type=read")
        # 匹配负号
        # result = re.sub(r'(?<!\d)-(\d)|(\d)-(\d)', replace_hyphen, msg)
        result=await convert_ranges_and_negatives(msg)
        print("result=", result)
        await speak(result,nerfreals[sessionid])
        # nerfreals[sessionid].put_msg_txt(msg)
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": "ok"}
            )
        )
    elif params['type'] == 'answer':
        qa_numb = params['qa_numb']
        qa = params["text"]
        print(f"qa: {qa}")
        qa = qa.replace("\n", "")
        # print(qa)  todo:对qa进行正则处理
        # qa = fix_invalid_json(qa)
        if user_id not in qa_data:
            qa_data[user_id] = []
        qa_data[user_id].append(qa)
        # qa_data（praams[text]）信息入库
        # res = await asyncio.get_event_loop().run_in_executor(None, restore_qa_data, user_id, params['text'],
        # nerfreals[sessionid], sessionid)
        if qa_numb == 0:
            # qa_numb 为0  qa_data入库
            print("qa_data入库")
            # res = await asyncio.get_event_loop().run_in_executor(None, restore_qa_data, user_id, qa_data[user_id],
            #nerfreals[sessionid], sessionid)
            res = await restore_qa_data(user_id, qa_data[user_id],nerfreals[sessionid],sessionid)
            qa_data[user_id] = []

            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": 0, "data": f"问答信息已记录，正在生成总结...",
                     "total_interpret": True, "start_summary":True}
                )
            )
        else:
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": 0, "data": "回答已存入内存", "total_interpret": False}
                )
            )
    elif params['type'] == 'chat':

        # HRA解析
        if params['report_interpret']:

            # 此时无qa_data,生成qa_data
            if params['total_interpret'] is not True:
                print("获取hra解析及问题")
                # res = await asyncio.get_event_loop().run_in_executor(None, get_quertions_hra, user_id)
                res= await get_quertions_hra(user_id)

                # 对res["data"]的符号进行处理
                result = res["data"]
                for item in result:
                    # 对符号进行处理
                    item["interpretation"] = await convert_ranges_and_negatives(item["interpretation"])



                #nerfreals[sessionid].put_msg_txt(res["data"])

                # mm=json.dumps(res["data"])
                # result = re.sub(r'(?<!\d)-(\d)|(\d)-(\d)', replace_hyphen, mm)
                # result=json.loads(result)

                await speak(res["message"], nerfreals[sessionid])
                # nerfreals[sessionid].put_msg_txt(res["message"])


                return web.Response(
                    content_type="application/json",
                    text=json.dumps(
                        {"code": 0, "data": result, "is_qa": True}
                    )
                )
            else:

                # qa_data , user_id , kb_id 调用/normal_model_qa/接口，total_interpret = true
                print("hra总结")
                # 查询qa_data  这里有问题，不知道是不是入数据的问题
                qas = await get_question(user_id)
                print(type(qas))
                print(f"查询到qa:print( {qas}")
                qas = '[' + qas +']'
                print(qas)
                qa = json.loads(qas)
                QA_DATA= []
                print(type(qa))
                for item in qa:
                    QA_DATA.append(item)
                res = await asyncio.get_event_loop().run_in_executor(None, normal_model_qa,
                                                                     user_id,params['total_interpret'],
                                                                     params['text'],QA_DATA,
                                                                     nerfreals[sessionid])
                # 数字人读
                msg=res["data"]
                # msg=msg.replace("-","负")
                nerfreals[sessionid].put_msg_txt(msg)
                return web.Response(
                    content_type="application/json",
                    text=json.dumps(
                        {"code": 0, "data": msg}
                    )
                )
        # 普通RAG问答
        else:
            print("普通rag问答")
            res = await asyncio.get_event_loop().run_in_executor(None, normal_model, user_id,
                                                                 False,params['text'],[],
                                                                 nerfreals[sessionid])
            # print(res)
            if res["code"]==0:
                # 数字人读
                nerfreals[sessionid].put_msg_txt(res["data"])
                return web.Response(
                    content_type="application/json",
                    text=json.dumps(
                        {"code": 0, "data": res["data"]}
                    ),
                )
            else:
                return web.Response(
                    content_type="application/json",
                    text=json.dumps(
                        {"code": 500, "data": "获取llm回答失败"}
                    ),
                )
        # nerfreals[sessionid].put_msg_txt(res)
    elif params['type']=='radar':

        res = await asyncio.get_event_loop().run_in_executor(None, llm_response_radar, params['text'],
                                                             nerfreals[sessionid])
        #return "成功"

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": res}
            ),
        )


    '''elif params['type'] == 'read':
        nerfreals[sessionid].put_msg_txt(params['text'])
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": "ok"}
            )
        )
    elif params['type'] == 'answer':
        qa_data = params['text']

        # qa_data（praams[text]）信息入库
        res = await asyncio.get_event_loop().run_in_executor(None, restore_qa_data, user_id, qa_data,
                                                             nerfreals[sessionid], sessionid)
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": res}
            )
        )
    elif params['type'] == 'chat':
        # HRA解析
        if params['report_interpret']:
            # 此时无qa_data,生产qa_data
            qa_data = False
            if qa_data is not True:
                res = await asyncio.get_event_loop().run_in_executor(None, get_quertions_hra, user_id)

                # try :
                # qa_data入库，在内存/redis设置qa_data
                # asdad

                return web.Response(
                    content_type="application/json",
                    text=json.dumps(
                        {"code": 0, "data": res["data"], "is_qa": True}
                    )
                )
            else:
                # qa_data , user_id , kb_id 调用/normal_model_qa/接口，total_interpret = true
                res = await asyncio.get_event_loop().run_in_executor(None, llm_response, params['text'],
                                                                     nerfreals[sessionid])
                return web.Response(
                    content_type="application/json",
                    text=json.dumps(
                        {"code": 0, "data": res["data"]}
                    )
                )
        # 普通RAG问答
        else:
            res = await asyncio.get_event_loop().run_in_executor(None, llm_response, params['text'],
                                                                 nerfreals[sessionid])
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": 0, "data": res}
                ),
            )
        #nerfreals[sessionid].put_msg_txt(res)'''

async def convert_ranges_and_negatives(text):
    # 1. 处理范围符号~（半角和全角）
    text = re.sub(r'(?<![\d\w])([+-]?\d+(?:\.\d+)?)[~～]([+-]?\d+(?:\.\d+)?)', r'\1至\2', text)

    # 2. 优化负号处理：允许负号前为汉字、标点等非数字字符
    text = re.sub(r'(?<![\d])-(\d+(?:\.\d+)?)', r'负\1', text)  # 关键修改此处
    # 3.加号处理
    text=text.replace("+","正")
    # 4.去除#
    text = text.replace("#", "")
    #5.去除*
    text = text.replace("*", "")
    # 6. 处理连字符-范围
    text = re.sub(r'(?<![\d.])(\d+(?:\.\d+)?)\-(\d+(?:\.\d+)?)', r'\1至\2', text)
    #7. 处理小数点
    text = re.sub(r'(?<![\d.])(\d+(?:\.\d+)?)\.(\d+(?:\.\d+)?)', r'\1点\2', text)
    #8.处理字母后面加空格
    text = re.sub(r'([a-zA-Z])', r'\1 ', text)
    return text


# 正则匹配负号
def replace_hyphen(match):

    if match.group(2):  # 匹配到数字-数字的情况
        return f"{match.group(2)}至{match.group(3)}"
    else:  # 匹配到-数字的情况
        return f"负{match.group(1)}"

async def fix_invalid_json(json_str):
    """清理JSON字符串中的非法控制字符"""
    # 移除ASCII码0-31的控制字符（保留\n\t\r等常见转义字符）
    cleaned_str = re.sub(r'[\x00-\x1F](?![\n\t\r])', '', json_str)
    return cleaned_str
async def parse_json_safely(json_str):
    """安全解析JSON，自动清理非法字符"""
    try:
        # 先尝试直接解析
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"原始解析错误: {e}")
        # 清理非法字符后重试
        fixed_str = fix_invalid_json(json_str)
        try:
            return json.loads(fixed_str)
        except json.JSONDecodeError as e:
            print(f"清理后仍报错: {e}")
            raise


async def humanaudio(request):
    try:
        form= await request.post()
        sessionid = int(form.get('sessionid',0))
        fileobj = form["file"]
        filename=fileobj.filename
        filebytes=fileobj.file.read()
        nerfreals[sessionid].put_audio_file(filebytes)

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except Exception as e:
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg":"err","data": ""+e.args[0]+""}
            ),
        )

async def set_audiotype(request):
    params = await request.json()

    sessionid = params.get('sessionid',0)
    nerfreals[sessionid].set_custom_state(params['audiotype'],params['reinit'])

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"code": 0, "data":"ok"}
        ),
    )

async def record(request):
    params = await request.json()

    sessionid = params.get('sessionid',0)
    if params['type']=='start_record':
        # nerfreals[sessionid].put_msg_txt(params['text'])
        nerfreals[sessionid].start_recording()
    elif params['type']=='end_record':
        nerfreals[sessionid].stop_recording()
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"code": 0, "data":"ok"}
        ),
    )

async def is_speaking(request):
    params = await request.json()

    sessionid = params.get('sessionid',0)
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"code": 0, "data": nerfreals[sessionid].is_speaking()}
        ),
    )


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

async def post(url,data):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url,data=data) as response:
                return await response.text()
    except aiohttp.ClientError as e:
        logger.info(f'Error: {e}')

async def run(push_url,sessionid):
    nerfreal = await asyncio.get_event_loop().run_in_executor(None, build_nerfreal,sessionid)
    nerfreals[sessionid] = nerfreal

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    player = HumanPlayer(nerfreals[sessionid])
    audio_sender = pc.addTrack(player.audio)
    video_sender = pc.addTrack(player.video)

    await pc.setLocalDescription(await pc.createOffer())
    answer = await post(push_url,pc.localDescription.sdp)
    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer,type='answer'))
##########################################
# os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
# os.environ['MULTIPROCESSING_METHOD'] = 'forkserver'
if __name__ == '__main__':
    mp.set_start_method('spawn')
    parser = argparse.ArgumentParser()

    # audio FPS
    parser.add_argument('--fps', type=int, default=50, help="audio fps,must be 50")
    # sliding window left-middle-right length (unit: 20ms)
    parser.add_argument('-l', type=int, default=10)
    parser.add_argument('-m', type=int, default=8)
    parser.add_argument('-r', type=int, default=10)

    parser.add_argument('--W', type=int, default=450, help="GUI width")
    parser.add_argument('--H', type=int, default=450, help="GUI height")

    #musetalk opt
    parser.add_argument('--avatar_id', type=str, default='avator_1', help="define which avatar in data/avatars")
    #parser.add_argument('--bbox_shift', type=int, default=5)
    parser.add_argument('--batch_size', type=int, default=16, help="infer batch")

    parser.add_argument('--customvideo_config', type=str, default='', help="custom action json")

    parser.add_argument('--tts', type=str, default='edgetts', help="tts service type") #xtts gpt-sovits cosyvoice
    #parser.add_argument('--REF_FILE', type=str, default="zh-CN-YunxiaNeural")
    parser.add_argument('--REF_FILE', type=str, default="zh-CN-XiaoxiaoNeural")
    parser.add_argument('--REF_TEXT', type=str, default=None)
    parser.add_argument('--TTS_SERVER', type=str, default='http://127.0.0.1:9880') # http://localhost:9000
    # parser.add_argument('--CHARACTER', type=str, default='test')
    # parser.add_argument('--EMOTION', type=str, default='default')

    parser.add_argument('--model', type=str, default='musetalk') #musetalk wav2lip ultralight

    parser.add_argument('--transport', type=str, default='rtcpush') #webrtc rtcpush virtualcam
    parser.add_argument('--push_url', type=str, default='http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream') #rtmp://localhost/live/livestream

    parser.add_argument('--max_session', type=int, default=1)  #multi session count
    parser.add_argument('--listenport', type=int, default=8010, help="web listen port")

    opt = parser.parse_args()
    #app.config.from_object(opt)
    #print(app.config)
    opt.customopt = []
    if opt.customvideo_config!='':
        with open(opt.customvideo_config,'r') as file:
            opt.customopt = json.load(file)

    # if opt.model == 'ernerf':
    #     from nerfreal import NeRFReal,load_model,load_avatar
    #     model = load_model(opt)
    #     avatar = load_avatar(opt)
    if opt.model == 'musetalk':
        from musereal import MuseReal,load_model,load_avatar,warm_up
        logger.info(opt)
        model = load_model()
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size,model)
    elif opt.model == 'wav2lip':
        from lipreal import LipReal,load_model,load_avatar,warm_up
        logger.info(opt)
        model = load_model("./models/wav2lip.pth")
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size,model,256)
    elif opt.model == 'ultralight':
        from lightreal import LightReal,load_model,load_avatar,warm_up
        logger.info(opt)
        model = load_model(opt)
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size,avatar,160)

    # if opt.transport=='rtmp':
    #     thread_quit = Event()
    #     nerfreals[0] = build_nerfreal(0)
    #     rendthrd = Thread(target=nerfreals[0].render,args=(thread_quit,))
    #     rendthrd.start()
    if opt.transport=='virtualcam':
        thread_quit = Event()
        nerfreals[0] = build_nerfreal(0)
        rendthrd = Thread(target=nerfreals[0].render,args=(thread_quit,))
        rendthrd.start()

    #############################################################################
    appasync = web.Application(client_max_size=1024**2*100)
    appasync.on_shutdown.append(on_shutdown)
    appasync.router.add_post("/offer", offer)
    appasync.router.add_post("/human", human)
    appasync.router.add_post("/hraHuman", hraHuman)
    appasync.router.add_post("/hra_t", hra_t)
    appasync.router.add_post("/humanaudio", humanaudio)
    appasync.router.add_post("/set_audiotype", set_audiotype)
    appasync.router.add_post("/record", record)
    appasync.router.add_post("/is_speaking", is_speaking)
    appasync.router.add_static('/',path='web')

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(appasync, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    # Configure CORS on all routes.
    for route in list(appasync.router.routes()):
        cors.add(route)

    pagename='webrtcapi.html'
    if opt.transport=='rtmp':
        pagename='echoapi.html'
    elif opt.transport=='rtcpush':
        pagename='rtcpushapi.html'
    logger.info('start http server; http://<serverip>:'+str(opt.listenport)+'/'+pagename)
    logger.info('如果使用webrtc，推荐访问webrtc集成前端: http://222.30.145.22:'+str(opt.listenport)+'/dashboard.html')
    def run_server(runner):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, '0.0.0.0', opt.listenport)
        loop.run_until_complete(site.start())
        if opt.transport=='rtcpush':
            for k in range(opt.max_session):
                push_url = opt.push_url
                if k!=0:
                    push_url = opt.push_url+str(k)
                loop.run_until_complete(run(push_url,k))
        loop.run_forever()
    #Thread(target=run_server, args=(web.AppRunner(appasync),)).start()
    run_server(web.AppRunner(appasync))

    #app.on_shutdown.append(on_shutdown)
    #app.router.add_post("/offer", offer)

    # print('start websocket server')
    # server = pywsgi.WSGIServer(('0.0.0.0', 8000), app, handler_class=WebSocketHandler)
    # server.serve_forever()


