import time
import os
from marshal import dumps

from openai import timeout

from basereal import BaseReal
from logger import logger
import json
import requests
from aiohttp import web
from datetime import datetime
from database_utils import get_db, create_qa_data, get_qa_data, get_qa_data_by_user, update_qa_data
import asyncio  # 新增：用于异步操作


def postRequests(str1):
    try:
        url = 'http://222.30.145.22:8100/conversations/api/np_get_res'
        data = {"message": str1}
        response = requests.post(url, data=json.dumps(data))
        return response.json()
    except Exception as e:
        print("交互异常:", str(e))


async def getQuestionsHRA(user_id):
    try:
        url = 'http://222.30.145.22:8100/v1/knowledge_base_chat_with_hra/'
        data = {
            "user_id": user_id,
            "kb_id": "2",
            "report_interpret": True
        }
        # print(f"hra接口:{url}")
        # 此处为模拟响应，实际应取消注释下方请求代码
        # print("调用前")
        #response = requests.post(url, data=json.dumps(data))
        response = await asyncio.to_thread(
            requests.post,
            url,
            json=data,
            timeout=1200)
        # print("调用后")
        # response = {
        #     "code": 200,
        #     "message": "成功获取HRA报告解读",
        #     "data": [
        #         {
        #             "system_name": "酸碱平衡",
        #             "interpretation": "根据检测数据，您的PaCO2为53.2毫米汞柱，高于正常范围（35-45毫米汞柱），[H+]为53.65纳摩尔/升，高于正常范围（42.6-51.3纳摩尔/升）。这表明您可能存在酸碱平衡失调，具体表现为呼吸性酸中毒或代谢性酸中毒。这种情况可能导致疲劳、呼吸困难、头晕等症状，长期可能影响心脏和肾脏功能。建议您及时就医，进行详细检查，包括血气分析和代谢评估，并根据医生建议调整生活习惯，如戒烟、适量运动等，以改善呼吸状态和整体健康状况。",
        #             "questions": "是否长期服用碳酸氢钠或抗酸药物?"
        #
        #         },
        #         {
        #             "system_name": "激素水平",
        #             "interpretation": "根据检测数据，您的醛固酮水平为27.0 ng/dL，高于正常范围（0.1-20.0 ng/dL），提示可能存在醛固酮增多症。醛固酮升高会导致钠潴留、钾排泄增加，可能引起高血压和低血钾。肾上腺髓质激素分泌量为37.0，远超正常范围（-20~+20），提示肾上腺髓质激素分泌过多，可能与肾上腺髓质增生或嗜铬细胞瘤等疾病相关。建议您及时就医，进行血浆醛固酮浓度、肾上腺CT等进一步检查，明确病因。同时，建议调整生活方式，低盐饮食，适度运动，并在医生指导下使用降压药物，控制血压。",
        #             "questions": "近期月经周期是否规律，有无提前、推迟或闭经情况?经量是否异常(过多 / 过少)?"
        #         },
                # {
                #     "system_name": "呼吸系统",
                #     "interpretation": "根据HRA检测数据，您的呼吸系统存在以下异常指标：\n\n1.   气管附近区域  和  支气管区域  的电阻抗值均为37.0，超出参考范围（-20～+20）。这表明局部组织可能存在炎症或异常变化。\n\n2.   健康风险分析  ：您可能存在支气管炎、气喘或耳鼻喉炎症的风险，伴随换气不足和血碳酸偏高，可能影响呼吸功能。\n\n  初步建议  ：\n- 尽快就医，进行肺功能检查或影像学检查以明确诊断。\n- 避免吸烟和空气污染，保持呼吸道湿润。\n- 适当锻炼，增强呼吸功能。\n\n建议及时就医，以获得专业诊断和治疗。",
                #     "questions": "近期是否有咳嗽、咳痰的情况?痰液颜色和性质如何(如白色泡沫痰、黄色脓痰、带血痰等)?"
                # },
                # {
                #     "system_name": "消化系统",
                #     "interpretation": "根据检测数据，您的消化系统存在以下异常指标：\n\n1.   降结肠区域：-24.0    \n   低于参考值，提示该区域可能存在血液循环不足或功能减弱。\n\n2.   十二指肠区域：21.0    \n   高于参考值，可能提示局部充血或炎症。\n\n3.   胃区域：21.0    \n   高于参考值，可能提示胃部充血或炎症。\n\n4.   食道上段：37.0    \n   高于参考值，可能提示食道反流或炎症。\n\n  健康风险：    \n您可能存在胃炎、十二指肠炎或食道反流等问题，建议避免辛辣、油腻饮食，少量多餐，保持良好姿势，避免饭后立即躺下。建议就医进一步检查，如胃镜或结肠镜检查，以明确病因并及时治疗。",
                #     "questions": "有无腹痛、腹胀或腹部不适?具体位置?"
                # },
                # {
                #     "system_name": "五官",
                #     "interpretation": "1.   异常指标含义  ：右侧鼻前庭和固有鼻腔区域的检测值为26.0，提示该区域可能存在炎症、肿胀或其他异常情况，可能与鼻炎、鼻窦炎或鼻腔结构问题相关。\n\n2.   健康风险  ：鼻腔疾病可能导致黏膜刺激症状、呼吸及嗅觉功能障碍，严重时可能引发颅内并发症（如脑膜炎、海绵窦感染）或全身性疾病的表现（如贫血、内分泌疾病等）。\n\n3.   健康建议  ：建议及时就医，进行鼻部专科检查（如鼻内镜、CT等），明确病因。保持鼻腔清洁，避免接触刺激物，必要时使用鼻腔保湿剂。如伴有全身症状（如贫血、内分泌异常等），需进一步检查全身健康状况。\n\n请尽快就医，避免延误治疗。",
                #     "questions": "眼睛是否经常干涩、发痒、流泪或有异物感?"
                # },
                # {
                #     "system_name": "泌尿系统",
                #     "interpretation": "根据检测数据，左肾及输尿管区域的生物活性状态为-24.0，低于参考值范围（-20～+20），提示该区域可能存在供血不足或功能减退的情况；右肾及输尿管区域的生物活性状态为21.0，高于参考值范围，提示该区域可能存在充血或炎症的风险。建议及时就医，进行泌尿系统的详细检查，如B超或尿常规等，以排除尿路感染、结石或其他潜在疾病的可能性。同时，建议保持良好的生活习惯，多喝水，避免高盐、高蛋白饮食，以减轻肾脏负担。定期监测相关指标，以便及时调整治疗方案。",
                #     "questions": "有无尿频、尿急、尿痛或排尿困难?"
                # },
                # {
                #     "system_name": "神经系统",
                #     "interpretation": "根据检测数据，丘脑和下丘脑区域的数值偏高，超出正常范围（-20～+20）。丘脑和下丘脑的异常可能与压力过大或植物神经系统失调有关。下丘脑作为调节内分泌和自主神经功能的重要中枢，其异常可能导致激素分泌紊乱，进而影响情绪、睡眠、心率等生理功能。\n\n建议患者注意调整生活方式，减少压力，保持规律作息和健康饮食。可尝试冥想、深呼吸等放松技巧，适当进行有氧运动（如散步、慢跑），以改善自主神经功能。如症状持续或加重，建议及时就医，进行进一步检查和治疗。",
                #     "questions": "有无头痛、头晕或眩晕?性质和频率如何?"
                # },
                # {
                #     "system_name": "内分泌系统",
                #     "interpretation": "根据检测数据，您的甲状腺区域和肾上腺髓质指标超出正常范围，提示可能存在甲状腺功能亢进和肾上腺功能异常。甲状腺功能亢进可能导致心悸、体重减轻、情绪波动等症状，而肾上腺问题可能引起血压波动或电解质失衡。建议您进一步检查甲状腺功能和肾上腺激素水平，同时注意饮食调节，减少咖啡因摄入，保持良好的生活习惯，并定期监测健康状况。如有不适，请及时就医。",
                #     "questions": "是否出现脖子增粗或甲状腺肿大?"
                # },
                # {
                #     "system_name": "心血管系统",
                #     "interpretation": "根据检测数据，您的心血管系统存在以下异常指标：右前庭压力感受器和左前庭压力感受器数值偏高，提示自主神经功能失调，可能影响血压调节；右颈动脉和左颈动脉数值偏高，提示血管张力异常，增加动脉硬化或高血压风险；左右手、上臂、前臂神经血管束数值偏高，提示这些区域的血管张力增加；左腿、小腿、脚神经血管束数值偏低，提示下肢血液循环不良，存在缺血风险；门脉循环数值偏高，提示肝脏供血不足，可能影响代谢功能。建议您注意低盐低脂饮食，适量运动，戒烟限酒，定期监测血压和血脂，必要时就医检查。",
                #     "questions": "有无胸闷、胸痛或心前区不适?性质如何?"
                # },
                # {
                #     "system_name": "骨骼系统",
                #     "interpretation": "根据HRA检测数据，您的骨骼系统中C5、C6、C7、Th1、Th2、Th3指标异常，提示可能存在骨关节功能改变，导致脊椎阻滞，进而引发疼痛。此外，左臂和右臂的神经肌肉可能过分兴奋，增加神经痛或麻木的风险。\n\n建议您及时就医，进行详细骨科检查，如X光或MRI，以明确病因。同时，可考虑物理治疗，如牵引、推拿等，缓解症状。日常生活中，避免长时间保持一个姿势，适当进行颈部和肩部的拉伸运动，增强肌肉力量。饮食上，增加钙和维生素D的摄入，有助于骨骼健康。",
                #     "questions": "是否经常出现关节疼痛、肿胀或僵硬(尤其晨起时)?"
                # }
        #     ]
        # }
        # print(f"hra接口：{response.json()}")
        # response = {
        #     "code": 200,
        #     "message": "成功获取HRA报告解读",
        #     "data":[    {      "system_name": "神经系统",      "interpretation": "您的丘脑值为27.0，高于正常范围（负20~20），这可能表明您的丘脑存在功能障碍。您的下丘脑区域值为21.0，高于正常范围（负20~20），这可能表明您的下丘脑存在功能障碍。建议您注意神经系统的健康，保持良好的作息，避免过度劳累，必要时就医。",      "question": "您最近是否有出现头痛、失眠、情绪异常或体温调节紊乱等不适症状呢？"    },    {      "system_name": "消化系统",      "interpretation": "您的降结肠区域值为负24.0，低于正常范围（负20~20），这可能表明您的消化系统存在问题，如结肠炎或结肠功能障碍。您的十二指肠区域值为21.0，高于正常范围（负20~20），这可能表明您的十二指肠存在炎症或溃疡。您的胃区域值为21.0，高于正常范围（负20~20），这可能表明您的胃存在炎症或溃疡。您的食道上段值为37.0，高于正常范围（负20~20），这可能表明您的食道存在炎症或溃疡。建议您注意消化系统的健康，饮食清淡，避免辛辣刺激性食物",      "question": "您近期是否有出现腹痛、腹泻、反酸、烧心或吞咽不适等消化系统相关症状呢？"    },    {      "system_name": "内分泌系统",      "interpretation": "您的促甲状腺激素值为负15.0，低于正常范围（负2~10），这可能表明存在甲状腺功能亢进的倾向。甲状腺区域值为42.0，甲状腺左、右叶区域值均为33.0，均高于正常范围（负20~20），提示甲状腺组织可能存在代偿性增生或功能活跃。醛固酮值为27.0，略高于正常范围（10~19），可能与肾上腺皮质功能轻度异常相关。建议您关注甲状腺功能，定期复查激素水平，避免高碘饮食。",      "question": "您最近是否有出现心慌、手抖、多汗、体重下降或情绪易激动等甲状腺功能亢进相关症状呢？"    },    {      "system_name": "心血管系统",      "interpretation": "您的右颈动脉值为48.0，左颈动脉值为40.0，均显著高于正常范围（负20~20），可能提示颈动脉血管张力增高或存在动脉硬化早期表现。冠状血管值为19.0，处于正常上限，需关注心肌供血情况。左心室值为负15.0，低于正常范围，可能反映左心室功能轻度异常。建议您控制血压、血脂，避免高脂饮食，适当增加有氧运动。",      "question": "您近期是否有出现胸闷、胸痛、心悸或活动后气短等心血管不适症状呢？"    },    {      "system_name": "呼吸系统",      "interpretation": "您的右肺中叶区域值为负17.0，左肺下叶区域值为负15.0，均低于正常范围（负20~20），可能提示肺部通气功能轻度下降或局部肺组织顺应性降低。支气管区域值为37.0，显著高于正常范围，需警惕支气管炎症或痉挛。呼吸系统状态说明中提到'呼吸器官疾病可能性'及'血碳酸偏高'，进一步支持通气功能障碍。建议您避免接触烟雾及刺激性气体，必要时进行肺功能检查。",      "question": "您是否有出现咳嗽、咳痰、喘息或活动后呼吸困难等呼吸系统症状呢？"    },    {      "system_name": "骨骼系统",      "interpretation": "您的C6-C8颈椎区域值（33.0、33.0、37.0）及Th1-Th2胸椎值（36.0、33.0）显著高于正常范围，提示颈椎及上胸椎可能存在关节功能紊乱或肌肉紧张。L2-L3腰椎值为负16.0，低于正常范围，可能与腰椎间盘压力异常相关。状态说明中提到'脊椎阻滞引起的疼痛'及'神经肌肉过分兴奋风险'，建议您注意坐姿睡姿，避免久坐，可进行康复理疗。",      "question": "您是否有出现颈肩部疼痛、腰痛或肢体麻木、乏力等骨骼肌肉系统症状呢？"    },    {      "system_name": "泌尿生殖系统",      "interpretation": "您的左肾及输尿管区域值为负24.0，低于正常范围，可能提示左肾血流灌注异常或输尿管张力改变。右肾及输尿管区域值为21.0，略高于正常范围，需关注右肾代谢状态。膀胱区域值为负17.0，低于正常范围，可能与膀胱逼尿肌功能异常相关。状态说明中提到'肾功能轻度改变'，建议您保持充足饮水，避免憋尿，定期复查尿常规。",      "question": "您近期是否有出现尿频、尿急、尿痛或腰酸等泌尿系统不适症状呢？"    },    {      "system_name": "免疫系统",      "interpretation": "您的胸腺值为19.0，处于正常范围（负20~20），提示胸腺功能基本正常。状态说明中提到'自身免疫性疾病倾向'及'免疫球蛋白轻度增加'，虽无明确指标异常，但需关注长期免疫平衡。建议您保持规律作息，避免过度劳累，均衡饮食以维持免疫功能。",      "question": "您是否有出现反复感染、关节肿痛或皮肤红斑等自身免疫相关症状呢？"    }  ]
        #
        #
        # }

        return response.json()  #.json()
    except Exception as e:
        print("交互异常:", str(e))


def postRadar(user_id, datas):
    try:
        url = "http://222.30.145.22:8100/processRadarData"
        data = {
            "user_id": user_id,
            "data": datas
        }
        response = requests.post(url, data=json.dumps(data), timeout=60)
        return response.json()
    except Exception as e:
        print("交互异常:", str(e))


def postNormal(user_id: int, total_interpret: bool, query: str, qa_data: list[str]):
    try:
        url = "http://222.30.145.22:8100/normal_model_qa/"
        data = {
            "user_id": user_id,
            "total_interpret": total_interpret,
            "query": query,
            "qa_data": qa_data
        }
        response = requests.post(url, data=json.dumps(data), timeout=60)
        return response.json()
    except Exception as e:
        print("交互异常:", str(e))


def llm_response(message, nerfreal: BaseReal):
    # start = time.perf_counter()

    msg = postRequests(message)["response"]

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
    return msg


def llm_response_radar(message, nerfreal: BaseReal):
    json_data = json.loads(message)
    user_id = json_data["user_id"]
    data = json_data["data"]
    # print(user_id)
    res = postRadar(user_id, data)

    # print(res)
    msg = res["question"]
    # msg=msg.replace("-", "负")
    if res["code"] == 200:
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
        return msg
    elif (res["code"] == 204):
        nerfreal.put_msg_txt("雷达波检测无异常")
        return "雷达波检测无异常"
    else:
        nerfreal.put_msg_txt("遇到异常")
        return "遇到异常"


async def get_quertions_hra(user_id):
    res =await getQuestionsHRA(user_id)
    return res


def llm_response_hra(user_id: int, message, nerfreal: BaseReal, sessionid):
    return


# 修正1：使用异步函数并正确获取会话
async def restore_qa_data(user_id: int, qa_data: str, nerfreal: BaseReal, sessionid):
    # temp = qa_data
    # length = len(qa_data)
    # for index, qa in enumerate(qa_data):
    #     qa = "{" + str(qa) + "}"
    #     if index == length - 1:
    #         temp += qa
    #     else:
    #         temp += qa + ","
    # print(temp)

    # 正确方式：在异步函数中使用async for获取会话
    async for session in get_db():
        try:
            record = await create_qa_data(
                user_id=user_id,
                hra_qa_data=qa_data,
                qa_date=datetime.now()
            )
            return {
                "code": 200,
                "message": "qa_data存储成功",
                "data": f"{record.user_id}的问答记录已存储"
            }
        except Exception as e:
            print(f"数据库操作错误: {e}")
            return {
                "code": 500,
                "message": "qa_data存储失败",
                "data": str(e)
            }


def normal_model(user_id, total_interpret, query, qa_data, nerfreal: BaseReal):
    res = postNormal(user_id, total_interpret, query, qa_data)
    msg=res["answer"]
    # msg=msg.replace("-","负")
    # print(res)
    if res["code"] == 200:
        return {
            "code": 0,
            "message": "成功获取回答",
            "data": msg
        }
    else:
        return {
            "code": 500,
            "message": "LLM回答失败",
            "data": msg
        }


def normal_model_qa(user_id, total_interpret, query, qa_data, nerfreal: BaseReal):
    res = postNormal(user_id, total_interpret, query, qa_data)
    # print(res)
    if res["code"] == 200:
        # print(f"数据更新成功，总结如下：{res['summary']}")
        return {
            "code": 0,
            "message": res["message"],
            "data": res["summary"]
        }
    else:
        return {
            "code": 500,
            "message": res["message"],
            "data": res["summary"]
        }


# 修正2：异步函数获取问题
async def get_question(user_id):
    # 正确方式：在异步函数中使用async for获取会话
    async for session in get_db():
        try:
            # 调用异步获取数据的函数
            qa = await get_qa_data(user_id)
            if qa:
                # print(qa.hra_qa_data)
                # print(type(qa.hra_qa_data))
                return qa.hra_qa_data
            return None
        except Exception as e:
            print(f"获取问题错误: {e}")
            return None


# 修正3：异步更新QA数据
async def update_qa(user_id, hra_report_data, report_date):
    # 正确方式：在异步函数中使用async for获取会话
    async for session in get_db():
        try:
            # 先查询原有记录
            qa = await get_qa_data(user_id)
            if not qa:
                return None

            # 执行更新操作
            updated_qa = await update_qa_data(
                user_id=user_id,
                hra_report_data=hra_report_data,
                report_date=report_date
            )
            return updated_qa
        except Exception as e:
            print(f"更新QA数据错误: {e}")
            return None