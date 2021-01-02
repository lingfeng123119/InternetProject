from django.http import HttpResponse
from django.shortcuts import redirect, render
# 注：具体网络图如下所示
#           HostB
#             #
#             #
#           RouterB
#             #
#          #
#       #
#   RouterA # # # # # # RouterC
#             #
#             #
#           HostA

# 接收静态配置项
from internetPro.nat_config import NatSettings, nat_config


def setting(request):
    # 如果用户选择静态配置路由
    if request.GET.get("status"):
        # 接收ip、mask配置 格式为10.0.0.1/25
        routerA = request.GET.get("routerA")
        routerA_ip = routerA.split("/")[0]
        routerA_mask = routerA.split("/")[1]
        routerB = request.GET.get("routerB")
        routerB_ip = routerB.split("/")[0]
        routerB_mask = routerB.split("/")[1]
        routerA_mask = transfer_mask(routerA_mask)
        routerB_mask = transfer_mask(routerB_mask)

        # 接收映射表配置 格式为10.0.0.1
        hostA_ip = request.GET.get('hostA')
        routerC_ip = request.GET.get('routerC')

        # 后端处理
        nat_setting = NatSettings()
        nat_setting.rta['f0/0']['ip'] = routerA_ip
        nat_setting.rta['f0/0']['mask'] = routerA_mask
        nat_setting.rtb['f0/0']['ip'] = routerB_ip
        nat_setting.rtb['f0/0']['mask'] = routerB_mask
        nat_setting.host_a['ip'] = hostA_ip
        nat_setting.rtc['f0/0']['ip'] = routerC_ip

        is_success, message = nat_config(nat_setting)
        return HttpResponse(message)

    # 如果用户选择动态配置路由
    else :
        # 接收ip、mask配置 格式为10.0.0.1/25
        routerA = request.GET.get("routerA")
        routerA_ip = routerA.split("/")[0]
        routerA_mask = routerA.split("/")[1]
        routerB = request.GET.get("routerB")
        routerB_ip = routerB.split("/")[0]
        routerB_mask = routerB.split("/")[1]
        routerA_mask = transfer_mask(routerA_mask)
        routerB_mask = transfer_mask(routerB_mask)

        # 后端处理
        nat_setting = NatSettings()
        nat_setting.rta['f0/0']['ip'] = routerA_ip
        nat_setting.rta['f0/0']['mask'] = routerA_mask
        nat_setting.rtb['f0/0']['ip'] = routerB_ip
        nat_setting.rtb['f0/0']['mask'] = routerB_mask
        is_success, message = nat_config(nat_setting)
        return HttpResponse(message)










# mask转换
def transfer_mask(mask):
    mask_byte = ''
    for i in range(1,int(mask)) :
        mask_byte = mask_byte + '1'
    for j in range(int(mask), 32):
        mask_byte = mask_byte + '0'
    mask_int1 = int(mask_byte[0:8], 2)
    mask_int2 = int(mask_byte[8:16], 2)
    mask_int3 = int(mask_byte[16:24], 2)
    mask_int4 = int(mask_byte[24:33], 2)
    mask_int = "%d.%d.%d.%d" % (mask_int1,mask_int2,mask_int3,mask_int4)
    return mask_int

def a():
    print(1234+".")
a()





