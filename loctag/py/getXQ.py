import json
import os
from urllib import request,parse
import  loctag.py.DataTransform as tf
import loctag.py.CommonUtil as util

rc = util.ReadConfig('../config.conf')
xq = rc.getItems('getXQ')
#从hive导出的数据存放目录
file_path= xq['src']
save_path= xq['save_path']

# file_path='/opt/sunny/hive-export/original/000000_0'
# save_path='/opt/sunny/hive-export/match/'
file_name= xq['file_name']

ak = 'CKzzl0ODAd4kBl0TzXTl59F9Ne9Bzrgk'
url = 'http://api.map.baidu.com/geocoder/v2/?'


def sendRequest(lng,lat):
    '''
    请求百度的API
    :param lng: 经度
    :param lat: 维度
    :return: 类型是字典
    '''
    args={
        'callback':'',
        'location':"%s,%s"%(lat,lng),
        'output' :'json',
        'pois':'1',
        'ak':ak
    }
    url_args = parse.urlencode(args)
    req = request.Request(url+url_args)
    resp = request.urlopen(req)
    result = resp.read().decode('utf-8')
    #把返回的结果转换为dict
    json_result = json.loads(result)
    return json_result

def getLngLat():
    '''
    通过经纬度调用百度api获取小区和tag信息
    :return: 包含了小区和tag的list
    '''
    repeat_data=[]
    if not os.path.exists(file_path):
        raise IOError(file_path+" is not exists ")
    with open(file_path,'r+') as file:
        lines = file.readlines()
        for line in lines:

            line = line.rstrip('\n')
            fields = line.split('\t')
            if(len(fields)<13):
                continue
            lng = fields[12].strip()
            lat = fields[13].strip()
            polygon = ''
            if not fields[14] == '\\N':
                geos = fields[14].split(';')
                for geo in geos:
                    ll = geo.split(',')
                    bd = tf.bd09(float(ll[0].strip()), float(ll[1].strip()))
                    new_ll = tf.adapter(bd,dict(execute=bd.transform)).execute()
                    polygon+='%.6f  %.6f;'%(new_ll[0],new_ll[1])

            # 高德坐标转百度
            gc = tf.gcj02(float(lng), float(lat))
            lnglat = tf.adapter(gc,dict(execute=gc.transform())).execute()

            #把高德的经纬度转为百度经纬度
            fields[12] = lnglat[0]
            fields[13] = lnglat[1]
            #获取位置信息
            addr_info = sendRequest(lnglat[0],lnglat[1])

            addr = addr_info['result']['pois'][0]
            name = addr.get('name','Null')
            tag = addr.get('poiType','Null')
            str = '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%.6f,%.6f,%s'%(fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9],fields[10],fields[11],name,tag,fields[12],fields[13],polygon.rstrip(';'))
            repeat_data.append(str+'\n')

    return repeat_data
def __uniqueData(data):
    '''
    把hive中的去重，使用python根据b_code,小区名称完成去重
    :param data:比较完整的数据
    :return:去重后的数据
    '''
    runique=data.copy()
    rdata = data
    unique=[]
    for i in range(len(rdata)):
        ifd = rdata[i].split(',')
        for j in range(i+1,len(rdata)):
            if j>=len(rdata):
                continue
            jfd = rdata[j].split(',')
            if ifd[10] == jfd[10] and ifd[14] == jfd[14] :
                runique[j]=0
    for u in runique:
        if not u ==0:
            unique.append(u)
    return unique

def __saveData(data):
    '''
    把去重后的数据保存到本地目录中去
    :param data:
    :return:
    '''
    if not os.path.exists(save_path):
        os.system('mkdir %s'%save_path)
    save = open(save_path+file_name, 'w+')
    for d in data:
        save.write(d)
    save.flush()
    save.close()

def run():
    rd = getLngLat()
    unique_data = __uniqueData(rd)
    __saveData(unique_data)

