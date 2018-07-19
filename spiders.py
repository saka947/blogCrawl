# -*- coding: UTF-8 -*-
import requests
import re
from bs4 import BeautifulSoup as sp
from models import article
import MySQLdb
import threading
from time import ctime,sleep
import json

root='https://www.cnblogs.com/cate/all/'
#依靠传入findTagParam的参数返回一个json，json内容为{"Tags":"","Categories":""}这样的，可以获取tag
findTagUrl='https://www.cnblogs.com/mvc/blog/CategoriesTags.aspx'
findTagParam={'blogApp':'','blogId':'','postId':''}
headers = {'content-type': 'application/json'}
next='https://www.cnblogs.com/mvc/AggSite/PostList.aspx'
payload={"CategoryType":"AllPosts","ParentCategoryId":0,"CategoryId":0,"PageIndex":1,"TotalPostCount":4000,"ItemListActionName":"PostList"}
#批量获取链接缓存
def getPageLink(start,end):
    links=[]
    for i in range(start,end+1):
        payload['PageIndex']=i
        try:
            response = requests.post(next,headers=headers,data=json.dumps(payload))
            s = sp(response.text, 'lxml')
            link = s.findAll(class_='titlelnk')
            for j in link:
                links.append(j.get('href'))
        except Exception as e:
            print e
    return  links


#形成数据
def formdata(links):
    data=[]
    for i in links:
        try:
            html=requests.get(i).text
            soup=sp(html,'lxml')
            url=i
            title=soup.find('title').text
            tag=''
            category=''
            try:
                tag=getTagAndCateByLink(i,'Tags')
            except Exception:
                pass
            try:
                category=getTagAndCateByLink(i,'Categories')
            except Exception:
                pass
            try:
                catchhtml=soup.find(id='cnblogs_post_body')
                catchhtml=str(catchhtml)
                data.append(article(url, title, catchhtml,tag,category))
            except Exception:
                print(i+' has no main')
        except Exception as e:
            print e
    return data


def getTagAndCateByLink(link,k):
    try:
        # from link get blogApp
        p1 ='.com/[\s\S]*/p/'
        a = re.search(p1,link)
        blogApp=a.group()[5:-3]

        # from link get postId
        p2 = '/p/[\s\S]*.html'
        b = re.search(p2, link)
        postId = b.group()[3:-5]

        html = requests.get(link).text
        soup = sp(html, 'lxml')
        l = soup.findAll('script')
        p3 = 'cb_blogId=\d*,'
        for i in l:
            s = str(i)
            c = re.search(p3, s)
            if c is not None:
                blogId = c.group()[10:-1]

        findTagParam['blogApp'] = blogApp
        findTagParam['blogId'] = blogId
        findTagParam['postId'] = postId

        json_ = requests.get(findTagUrl, params=findTagParam).json()
        p4='>(\w*|\W*|[\u4e00-\u9fa5])+</a>'
        text=json_[k]
        t2 = text.split(',')
        # print(d.group()[1:-4])
        for t in t2:
            a = re.search(p4, t)
            b = a.group()[1:-4]
            k = k + b + ','
        if k=='Tags':
            return k[4:-1]
        else:
            return k[10:-1]
    except Exception:
        return ''

def cache(data):
    try:
        connect=MySQLdb.connect(user='root',db='blogcrawl',charset='utf8')
        cur=connect.cursor()
    except Exception:
        print 'cannot get database connection'
    for article in data:
        url=article.url
        title=article.title.encode('utf-8')
        html=article.html
        html = re.sub('\n', '', html)
        html = re.sub('"', '\'', html)
        tag=article.tag.encode('utf-8')
        category=article.category.encode('utf-8')
        insertMysql='insert into articles VALUES ("{0}","{1}","{2}","{3}","{4}")'.format(url,title,html,tag,category)
        try:
            cur.execute(insertMysql)
        except Exception as e:
            print('insert error')
            print(e)

    cur.close()
    connect.commit()
    print 'finished'


class MyThread(threading.Thread):
    def __init__(self,func,args,name=''):
        threading.Thread.__init__(self)
        self.name=name
        self.func=func
        self.args=args
    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception:
            return None





if __name__ == '__main__':
    li=[]
    threads=[]
    cache_threads=[]
    print 'start at',ctime()
    for i in range(200):
        t=MyThread(getPageLink,(i,i),getPageLink.__name__)
        threads.append(t)
        t.start()

    for tr in threads:
        tr.join()
        a=tr.get_result()
        for j in a:
            li.append(j)
    print('end at',ctime())
    li=list(set(li))
    print '共有'+str(len(li))+'条链接'

    print '开始缓存 at',ctime()
    for i in range(0,len(li),20):
        d=formdata(li[i:i+19])
        cache(d)


    print '结束缓存 at',ctime()








