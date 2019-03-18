#!/usr/bin/python
# -*- coding: utf-8 *-*
# requests   module is used for a web-access (via GUI for instanse)
# time       module is used for sleep operator, and for unique message id generating
# logging    module is used to manage logging to file(s)
# sys        module is used here to retreive arguments that are followed with this script launch
# subprocess module is used here to launch a zabbix_sender console command
# config.py is a configuration that could be overriden by command line arguments
import requests, time, logging, sys
from subprocess import Popen, PIPE, STDOUT
from config import arguments

log_path_name = './logs.log'
ussd_answer_wait_timer = 20
Data = {'send': 'Send'}
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
    i = 0
    a = ''
    result_list = []
    while i < len(xml_line):
        while i < len(xml_line) and xml_line[i:i+6] <> '<error':
            i += 1
        while i < len(xml_line) and xml_line[i:i+7] <> '</error':
            i += 1
            a = a + xml_line[i]
    b = a.replace('>Баланс: ', '>')
    c = b.split('>')
    for d in c:
        pos = d.find('.')
        if pos <> -1:
            result_list.append(d[0:pos + 3])
    logging.info( result_list )
    send_to_zabbix( result_list )
    return result_list

def send_to_zabbix( values_list ):
    for i in range(0,len(values_list)):
        console_exec( arguments['zabbix_sender_path'] + ' -z ' + arguments['zabbix_ip'] + ' -s ' + arguments['zabbix_hosts_unit'] + ' -k '  + arguments['zabbix_key' + str(i+1)] + ' -o ' + values_list[i] )

def send_message( lines, message_type ):
    for i in range(0,len(lines)):
        dat = Data
        dat.update( { 'line' : lines[i] } )
        if message_type == 'sms':
            dat.update( { 'action' : 'SMS', 'smscontent' : arguments['message'] } )
            dstnums = arguments['dstphonenumbers'].split(',')
            for j in range(0,len(dstnums)):
                dat.update( { 'telnum' : dstnums[j] , 'smskey' : str(int(round(time.time() * 1000000)))[8:] } )
                logging.info( dat )
                ses.post('http://' + arguments['user'] + ':' + arguments['passwd'] + '@' + arguments['our_gsm_gateway_ip'] + '/default/en_US/sms_info.html?type=' + message_type, data = dat).content
        if message_type == 'ussd':
            dat.update( { 'action' : 'USSD', 'telnum': balance_telnumber , 'smskey' : str(int(round(time.time() * 1000000)))[8:] } )
            logging.info( dat )
            ses.post('http://' + arguments['user'] + ':' + arguments['passwd'] + '@' + arguments['our_gsm_gateway_ip'] + '/default/en_US/sms_info.html?type=' + message_type, data = dat).content

def read_ussd_response_out_of_xml( session ):
    Answer = session.post('http://' + arguments['our_gsm_gateway_ip'] + '/default/en_US/send_sms_status.xml?u=' + arguments['user'] + '&p=' + arguments['passwd']).content
    logging.info( Answer )
    return Answer

def args_parse():
    for i in range(1,len(sys.argv)):
        if sys.argv[i][0:2] == '--':
            arguments.update({sys.argv[i][2:]: sys.argv[i+1]})
    logging.debug(arguments)
                
ses = requests.session()

args_parse()

if arguments['mode'] == 'ussd':
    send_message( arguments['ussdports'].split(',') , arguments['mode'] )
    time.sleep( ussd_answer_wait_timer )
    resp = read_ussd_response_out_of_xml( ses )
    parse_balances( resp )
elif arguments['mode'] == 'sms':
    #message = 'Hello mama. I have run out of money. Send me another 400000 USD.'
    send_message( arguments['smsports'].split(',') , arguments['mode'] )
