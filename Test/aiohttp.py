from aiohttp import web


# 处理POST请求的处理器
async def handle_hra(request):
    try:
        # 从请求中获取JSON数据
        data = await request.json()

        # 提取所需的参数
        user_id = data.get('user_id')
        text = data.get('text')
        interrupt = data.get('interrupt', False)
        qa_numb = data.get('qa_numb', 0)

        # 处理数据...
        print(f"收到来自用户 {user_id} 的请求")
        print(f"问题数量: {qa_numb}")

        # 准备响应数据
        response_data = {
            'status': 'success',
            'data': [
                {
                    'interpretation': '这是对问题的解释',
                    'questions': '这是问题'
                }
            ]
        }

        # 返回JSON响应
        return web.json_response(response_data)

    except Exception as e:
        # 错误处理
        return web.json_response(
            {'error': str(e)},
            status=400
        )


# 创建应用并设置路由
app = web.Application()
app.router.add_post('/hraHuman', handle_hra)
