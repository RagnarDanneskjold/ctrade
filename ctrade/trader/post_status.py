from ctrade import *
from ctrade.messages import *
from collections import OrderedDict
from datetime import datetime
from apscheduler.schedulers.background import BlockingScheduler


def update_slack(major=['ETH', 'LTC', 'XRP']):

	p = Poloniex()
	pairs = [i for i in p.currency_pairs if any([j for j in major if 'USDT_'+j in i])]
	pairs += [i for i in p.currency_pairs if any([j for j in major if 'BTC_'+j in i])]


	def build_dataset(currency_pairs, days_back, period):
	    out = {}
	    for i in currency_pairs:
	        completed = False
	        while not completed:
	            try:
	                t = p.chart(i, days_back, period).df
	                completed = True
	            except:
	                pass

	        last = (t['close'].iloc[-1] - t['open'].iloc[-1])/t['open'].iloc[-1]
	        last_day =  (t['close'].iloc[-1] - t['open'].iloc[-7])/t['open'].iloc[-7]
	        out[i] = (last, last_day)
	        
	    return OrderedDict(sorted(out.items(), key=lambda x: x[1][1], reverse=True))


	out = build_dataset(pairs, 2, '4h')

	def print_update(out):
	    time = datetime.now()

	    def rround(x):
	        return "{:+.2%}".format(np.round(x, 4))
	    
	    msg = "Crypto-update {} UTC\n".format(datetime.now().strftime("%Y-%m-%d %H:%M"))
	    for k,v in out.items():
	        four = rround(v[0])
	        day = rround(v[1])
	        msg += ("{} \tlast 4h = {:>7}  last day = {:>7}\n".format('/'.join(k.split('_')[::-1]), 
	        														  four, day)).expandtabs(10)
	        
	    return msg

	post_message('cryptobot', 
				 print_update(out), 
				 username='cryptobot', 
				 icon=':matrix:')

def main():

	# post_message('cryptobot', 
	# 			 'BOT IS RUNNING...', 
	# 			 username='cryptobot', 
	# 			 icon=':matrix:')

	scheduler = BlockingScheduler()
	scheduler.add_job(update_slack, 
					  'interval', hours=4,
					  start_date='2017-06-14 23:00:00')
	scheduler.start()

if __name__=='__main__':

	   main()
