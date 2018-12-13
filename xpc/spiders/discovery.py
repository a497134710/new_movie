# -*- coding: utf-8 -*-
import re
import json
import scrapy
from scrapy import Request


def convert_int(s):
    if not s:
        return 0
    return int(s.strip().replace(',', ''))


ci = convert_int


class DiscoverySpider(scrapy.Spider):
    name = 'discovery'
    allowed_domains = ['xinpianchang.com', 'openapi-vtom.vmovier.com']
    start_urls = ['http://www.xinpianchang.com/channel/index/sort-like?from=tabArticle']

    def parse(self, response):
        pid_list = response.xpath('//ul[@class="video-list"]/li/@data-articleid').extract()
        url = 'http://www.xinpianchang.com/a%s?from=ArticleList'
        for pid in pid_list:
            request = Request(url % pid, callback=self.parse_post)
            request.meta['pid'] = pid
            yield request

    def parse_post(self, response):
        post = dict()
        pid = response.meta['pid']
        post['pid'] = pid
        post['title'] = response.xpath(
            '//div[@class="title-wrap"]/h3/text()').get()
        post['video'] = response.xpath(
            '//video[@id="xpc_video"]/@src').get()
        post['vid'], = re.findall(r'vid: \"(\w+)\",', response.text)
        cates = response.xpath('//span[contains(@class, "cate")]')
        post['category'] = '|'.join(
            [''.join(
                [c.strip() for c in cate.xpath(
                    './/text()').extract()]) for cate in cates])
        post['video_format'] = response.xpath(
            '//span[contains(@class, "video-format")]/text()').get() or ''
        post['video_format'] = post['video_format'].strip()
        post['created_at'] = response.xpath(
            '//span[contains(@class, "update-time")]/i/text()').get()
        post['play_counts'] = response.xpath(
            '//i[contains(@class, "play-counts")]/@data-curplaycounts').get()
        post['like_counts'] = response.xpath(
            '//span[contains(@class, "like-counts")]/@data-counts'
        ).get()

        video_url = 'https://openapi-vtom.vmovier.com/v3/video/%s' \
                    '?expand=resource'
        request = Request(
            video_url % post['vid'], callback=self.parse_video)
        request.meta['post'] = post
        yield request

        comment_url = 'http://www.xinpianchang.com/article' \
                      '/filmplay/ts-getCommentApi?id=%s&page=1'
        request = Request(
            comment_url % pid, callback=self.parse_comment)
        yield request

        composer_url = 'http://www.xinpianchang.com/u%s?from=articleList'
        composer_list = response.xpath(
            '//div[@class="user-team"]//ul[@class="creator-list"]/li')
        for composer in composer_list:
            cid = composer.xpath('./a/@data-userid').get()
            cr = dict(pid=pid, cid=cid)
            cr['pcid'] = '%s_%s' % (pid, cid)
            cr['roles'] = composer.xpath('./div/span/text()').get()
            yield cr
            request = Request(composer_url % cid, callback=self.parse_composer)
            request.meta['cid'] = cid
            yield request

    def parse_video(self, response):
        post = response.meta['post']
        result = json.loads(response.text)
        post['video'] = result['data']['resource']['default']['url']
        post['preview'] = result['data']['video']['cover']
        post['duration'] = result['data']['video']['duration']
        yield post

    def parse_comment(self, response):
        result = json.loads(response.text)
        for c in result['data']['list']:
            comment = dict()
            comment['commentid'] = c['commentid']
            comment['pid'] = c['articleid']
            comment['content'] = c['content']
            comment['created_at'] = c['addtime_int']
            comment['like_counts'] = c['count_approve']
            comment['cid'] = c['userInfo']['userid']
            comment['uname'] = c['userInfo']['username']
            comment['avatar'] = c['userInfo']['face']
            comment['url'] = response.url
            if c['reply']:
                comment['reply'] = c['reply']['commentid']
            yield comment

        # 判断是否还有下一页
        next_page = result['data']['next_page_url']
        if next_page:
            request = Request(next_page, callback=self.parse_comment)
            yield request

    def parse_composer(self, response):
        cid = response.meta['cid']
        composer = dict(cid=cid)
        composer['banner'] = response.xpath(
            '//div[@class="banner-wrap"]/@style'
        ).re_first(r'background-image:url\((.+?)\)')
        composer['avatar'] = response.xpath(
            '//span[@class="avator-wrap-s"]/img/@src').get()
        composer['name'] = response.xpath(
            '//p[contains(@class, "creator-name")]/text()').get()
        composer['intro'] = response.xpath(
            '//p[contains(@class, "creator-desc")]/text()').get()
        composer['like_counts'] = ci(response.xpath('//span[contains(@class, "like-counts")]/text()').get())
        composer['fans_counts'] = ci(response.xpath('//span[contains(@class, "fans-counts")]/text()').get())
        composer['follow_counts'] = ci(response.xpath('//span[@class="follow-wrap"]/span[last()]/text()').get())
        composer['location'] = response.xpath('//span[contains(@class, "icon-location")]/following-sibling::span[1]/text()').get()
        composer['career'] = response.xpath('//span[contains(@class, "icon-career")]/following-sibling::span[1]/text()').get()
        yield composer
