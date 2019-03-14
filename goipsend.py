#!/usr/bin/python
# -*- coding: utf-8 *-*
# requests   module is used for a web-access (via GUI for instanse)
# time       module is used for sleep operator, and for unique message id generating
# logging    module is used to manage logging to file(s)
# sys        module is used here to retreive arguments that are followed with this script launch
# subprocess module is used here to launch a zabbix_sender console command
# config.py is a configuration that could be overriden by command line arguments
import requests
import time
import logging
import sys
from subprocess import Popen, PIPE, STDOUT
from xml.dom.minidom import parseString
from config import arguments


log_path_name = './logs.log'
ussd_answer_wait_timer = 10
balance_telnumber = '*100#'

loglevel = logging.INFO
logger = logging.getLogger("")
logger.setLevel(loglevel)
logging.basicConfig(
    filename = log_path_name,
    level = loglevel,
    format = '%(asctime)s - %(levelname)s - %(message)s',
)


def console_exec(cmd):
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    cmd_output = p.stdout.read()
    return cmd_output


def parse_balances(xml_line):
    dom = parseString(xml_line)
    result_list = []
    for n in range(1, 9):
        error = dom.getElementsByTagName('error'+str(n))[0].childNodes
        if error:
            error = error[0].data
            error = error.replace(u'Баланс: ', '')
            error = error.replace(u'р.',' ')
            balance = error.split(' ')[0]
            try:
                float(balance)
                result_list.append(str(balance))
            except:
                logging.warning('balance is not float: ' + balance)
                result_list.append('')
        else:
            result_list.append('')
    logging.info( result_list )
    return result_list


def send_to_zabbix(values_list, zabbix_sender_path, zabbix_ip, zabbix_hosts_unit, zabbix_keys):
    for id_value, value in enumerate(values_list):
        if id_value < len(zabbix_keys):
            console_exec(
                zabbix_sender_path + \
                ' -z ' + zabbix_ip + \
                ' -s ' + zabbix_hosts_unit + \
                ' -k '  + zabbix_keys[id_value] + \
                ' -o ' + value 
            )


def send_message(session, lines, message_type, user, passwd, our_gsm_gateway_ip, dstnums = None, smscontent = None):
    for line in lines:
        data = {'send': 'Send'}
        data.update({'line': str(line)})
        if message_type == 'sms':
            data['action'] = 'SMS'
            data['smscontent'] = smscontent,
            dstnums = dstnums.split(',')
            for dstnum in dstnums:
                data['telnum'] = dstnum
                data['smskey'] = get_smskey()
                logging.info(data)
                session.post(
                    'http://' + user + ':' + passwd + '@' + our_gsm_gateway_ip + \
                    '/default/en_US/sms_info.html?type=' + message_type,
                    data = data)
        if message_type == 'ussd':
            data['action'] = 'USSD',
            data['telnum'] = balance_telnumber
            data['smskey'] = get_smskey()
            logging.info(data)
            session.post(
                'http://' + user + \
                ':' + passwd + \
                '@' + our_gsm_gateway_ip + \
                '/default/en_US/sms_info.html?' + \
                'type=' + message_type,
                data = data)


def read_ussd_response_out_of_xml(session, our_gsm_gateway_ip, user, passwd):
    answer = session.post(
        'http://' + our_gsm_gateway_ip + \
        '/default/en_US/send_sms_status.xml?' + \
        'u=' + user + \
        '&p=' + passwd).content
    logging.info(answer)
    return answer


def args_parse(arguments):
    for i in range(1, len(sys.argv)):
        if sys.argv[i][0:2] == '--':
            arguments[sys.argv[i][2:]] = sys.argv[i+1]
    logging.debug(arguments)
    return arguments


def get_smskey():
    return str(int(round(time.time() * 1000000)))[8:]


def main(arguments):
    session = requests.session()
    arguments['mode'] = 'ussd'
    arguments = args_parse(arguments)
    if arguments['mode'] == 'ussd':
        send_message(
            session,
            lines = arguments['lines'],
            message_type = arguments['mode'],
            user = arguments['user'],
            passwd = arguments['passwd'],
            our_gsm_gateway_ip = arguments['our_gsm_gateway_ip'],
        )
        time.sleep(ussd_answer_wait_timer)
        resp = read_ussd_response_out_of_xml(
            session,
            our_gsm_gateway_ip = arguments['our_gsm_gateway_ip'],
            user = arguments['user'],
            passwd = arguments['passwd'],
        )
        result_list = parse_balances(resp)
        send_to_zabbix(
            result_list,
            zabbix_sender_path = arguments['zabbix_sender_path'],
            zabbix_ip = arguments['zabbix_ip'],
            zabbix_hosts_unit = arguments['zabbix_hosts_unit'],
            zabbix_keys = arguments['zabbix_keys']
        )
    elif arguments['mode'] == 'sms':
        send_message(arguments['smsports'].split(','), arguments['mode'])


if __name__ == "__main__":
    sys.exit(main(arguments))