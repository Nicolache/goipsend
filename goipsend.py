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
from config import arguments

log_path_name = './logs.log'
ussd_answer_wait_timer = 10
balance_telnumber = '*100#'
Headers = {'Accept': '*/*'}
arguments.update( {'mode' : 'ussd'} )

loglevel = logging.INFO
#loglevel = logging.DEBUG
logger = logging.getLogger("")
logger.setLevel(loglevel)
logging.basicConfig(filename = log_path_name, level = loglevel, format = '%(asctime)s - %(levelname)s - %(message)s')

def console_exec( cmd ):
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    cmd_output = p.stdout.read()
    return cmd_output

def parse_balances( xml_line ):
    result_list = []
    for line in xml_line.split('\n'):
        print line
        if '<error' in line:
            error = line.split('>')[1]
            if '<' in error:
                result_list.append('')
                continue
            error = error.replace('Баланс: ', '')
            error = error.replace('р.','')
            balance = error.split(' ')[0]
            try:
                float(balance)
                result_list.append(balance)
            except:
                pass
    print result_list
    logging.info( result_list )
    return result_list[:4]

def send_to_zabbix( values_list ):
    for id_value, value in enumerate(values_list, start=1):
        console_exec( arguments['zabbix_sender_path'] + ' -z ' + arguments['zabbix_ip'] + ' -s ' + arguments['zabbix_hosts_unit'] + ' -k '  + arguments['zabbix_key' + str(id_value)] + ' -o ' + value )

def send_message( lines, message_type ):
    for line in lines:
        data = {'send': 'Send'}
        data.update( { 'line' : str(line) } )
        if message_type == 'sms':
            data.update( { 'action' : 'SMS', 'smscontent' : arguments['message'] } )
            dstnums = arguments['dstphonenumbers'].split(',')
            for j in range(0,len(dstnums)):
                data.update( { 'telnum' : dstnums[j] , 'smskey' : get_smskey() } )
                logging.info( data )
                ses.post('http://' + arguments['user'] + ':' + arguments['passwd'] + '@' + arguments['our_gsm_gateway_ip'] + '/default/en_US/sms_info.html?type=' + message_type, data = data)
        if message_type == 'ussd':
            data.update( { 'action' : 'USSD', 'telnum': balance_telnumber , 'smskey' : get_smskey() } )
            logging.info( data )
            ses.post('http://' + arguments['user'] + ':' + arguments['passwd'] + '@' + arguments['our_gsm_gateway_ip'] + '/default/en_US/sms_info.html?type=' + message_type, data = data)

def read_ussd_response_out_of_xml( session ):
    Answer = session.post('http://' + arguments['our_gsm_gateway_ip'] + '/default/en_US/send_sms_status.xml?u=' + arguments['user'] + '&p=' + arguments['passwd']).content
    logging.info( Answer )
    return Answer

def args_parse():
    for i in range(1,len(sys.argv)):
        if sys.argv[i][0:2] == '--':
            arguments.update({sys.argv[i][2:]: sys.argv[i+1]})
    logging.debug(arguments)


def get_smskey():
    return str(int(round(time.time() * 1000000)))[8:]
                
ses = requests.session()

args_parse()

if arguments['mode'] == 'ussd':
    send_message( arguments['lines'], arguments['mode'] )
    time.sleep( ussd_answer_wait_timer )
    resp = read_ussd_response_out_of_xml( ses )
    result_list = parse_balances( resp )
    # send_to_zabbix( result_list )
elif arguments['mode'] == 'sms':
    #message = 'Hello mama. I have run out of money. Send me another 400000 USD.'
    send_message( arguments['smsports'].split(',') , arguments['mode'] )
