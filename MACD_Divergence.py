#Strategy combine of fundamental and technical part
#Fundamental: Choosing stock with high volatility and high liquidity
#Technical: MACD indicator + RSI

from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Indicators")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Indicators import *
from datetime import datetime
import numpy as np

# constants
BUY = 1
SELL = -1
NONE = 0

#RSI band threshold
BUY_THRESHOLD = 20
SELL_THRESHOLD = 80

# plot symbol
SYMBOL2PLOT = "KKR"

class MACD_Equity_Trade(QCAlgorithm):
    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.
        '''
        self.PortfolioValue = 100000
        #Back Test 2years historical data – Stocks with 3Y Rev CAGR as of 01/01/2018
        self.SetStartDate(2018, 1, 1)    #Set Start Date
        self.SetEndDate(2019, 12, 31)      #Set End Date
        #self.SetCash(self.PortfolioValue)             #Set Strategy Cash
        #self.equities = ["LNG", "NLY", "XPO", "AVGO", "SHOP", "CHTR", "VRTX", "QSR", "TSLA", "CBOE", "FB", "INCY", "CNC", "SPLK","WDAY", "ANET", "PANW", "NOW", "TAP", "SQ"]
        
        #Real Trading – Stocks with 3Y Rev CAGR as of 01/01/2020
        #self.SetStartDate(2020, 1, 1)    #Set Start Date
        #self.SetEndDate(2020, 10, 16)      #Set End Date
        self.SetCash(self.PortfolioValue)             #Set Strategy Cash
        self.equities = ["LYFT", "EXAS", "LNG", "FANG", "NTR", "ALNY", "SNAP", "XP", "TWLO", "SHOP", "OKTA", "CI", "UBER", "CBOE", "TSLA", "SSNC", "BIP", "KKR", "CXO", "ROKU"] 
        
        self.__dictMACD = dict()
        self.__dictRSI = dict()
        #
        self.__dictMACDWindow = dict()
        self.__dictPriceWindow = dict()
        #
        self.__dictBB = dict()
        self.__dictPrev = dict()
        
        for equity in self.equities:
            self.AddEquity(equity, Resolution.Daily)
        
            # define our daily macd(12,26) with a 9 day signal
            self.__dictMACD[equity] = self.MACD(equity, 12, 26, 9, MovingAverageType.Exponential, Resolution.Daily)
            self.__dictRSI[equity] = self.RSI(equity, 14,  MovingAverageType.Exponential, Resolution.Daily)
            self.__dictBB[equity] = self.BB(equity, 20, 2, MovingAverageType.Exponential, Resolution.Daily);
            # register the daily data of "SPY" to automatically update the indicator
            self.RegisterIndicator(equity, self.__dictRSI[equity], Resolution.Daily)
            self.__dictPrev[equity] = datetime.min
            #
            self.__dictMACDWindow[equity] = RollingWindow[float](6)
            self.__dictPriceWindow[equity] = RollingWindow[float](6)
            
        plotEquity = SYMBOL2PLOT
        
        self.PlotIndicator("MACD_SIGNAL", True, self.__dictMACD[plotEquity], self.__dictMACD[plotEquity].Signal)
        self.PlotIndicator("FAST_SLOW", self.__dictMACD[plotEquity].Fast, self.__dictMACD[plotEquity].Slow)
        self.PlotIndicator("RSI", self.__dictRSI[plotEquity])
        self.PlotIndicator("BB", self.__dictBB[plotEquity].LowerBand, self.__dictBB[plotEquity].MiddleBand, self.__dictBB[plotEquity].UpperBand)


        # equal equities allocation
        self.holdRatio = 1.0 / len(self.equities)
        

    def OnData(self, data):
        '''OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
        '''
        
        ## MACD Indicator
        def Indicator_MACD(symbol):
            if not self.__dictMACD[symbol].IsReady: return NONE

    
            # define a small tolerance on our checks to avoid bouncing
            
            # define a small tolerance on our checks to avoid bouncing
            # bigger tolerance will miss some opportunity
            # smaller tolerance will buy/sell on noise spike
            tolerance = 0.0025
    
            holdings = self.Portfolio[symbol].Quantity
            
            # crossover = (MACD - signal)
            # crossover +ve : crossover for buy momentum
            # crossover -ve : crossover for sell momentum
            # delta% = crossover / MACD_fast 
            signalDeltaPercent = (self.__dictMACD[symbol].Current.Value - self.__dictMACD[symbol].Signal.Current.Value)/self.__dictMACD[symbol].Fast.Current.Value
            
            RollingWindowUpdated(symbol, self.__dictMACD[symbol].Fast.Current.Value)
    
            # if our macd is greater than our signal, then let's go long
            if holdings <= 0 and signalDeltaPercent > tolerance:  # 0.01%
                # longterm says buy as well
                return BUY
            # of our macd is less than our signal, then let's go short
            elif holdings >= 0 and signalDeltaPercent < -tolerance:
                return SELL
    
            
            return NONE

        ## RSI Indicator
        def Indicator_RSI(symbol):
            # update the indicator value with the new input close price every day
            #if data.Bars.ContainsKey(equity):
            #    self.__dictRSI[equity].Update(data[equity].EndTime, data[equity].Close)
                
            # wait for our RSI to fully initialize
            if not self.__dictRSI[symbol].IsReady: return NONE
        
            # only once per day
            if self.__dictPrev[symbol].date() == self.Time.date(): return NONE
    
            holdings = self.Portfolio[symbol].Quantity

            if self.__dictRSI[symbol].Current.Value < BUY_THRESHOLD:
                return BUY;
            if self.__dictRSI[symbol].Current.Value > SELL_THRESHOLD:
                return SELL;

            return NONE
 
        def RollingWindowUpdated(symbol, updated):
            '''Adds updated values to rolling window'''
            
            #if (symbol != SYMBOL2PLOT): return
        
            #self.Debug("Updates : " + str(updated))
            self.__dictMACDWindow[symbol].Add(updated)  
            self.__dictPriceWindow[symbol].Add(self.Securities[symbol].Price)  
     
        def MACDevergence_BuySell(symbol):       
            if not self.__dictMACDWindow[symbol].IsReady : return NONE
            if not self.__dictPriceWindow[symbol].IsReady : return NONE
            
            ### MACD_Fast for Divergent check
            a = []
                
            for item in self.__dictMACDWindow[symbol]:
                a.append(item)
                    
            l_MACD_min = (np.diff(np.sign(np.diff(a))) > 0).nonzero()[0] + 1      # local min
            l_MACD_max = (np.diff(np.sign(np.diff(a))) < 0).nonzero()[0] + 1      # local max

            ### Price for Divergent check              
            a = []
                
            for item in self.__dictPriceWindow[symbol]:
                a.append(item)
                
            l_Price_min = (np.diff(np.sign(np.diff(a))) > 0).nonzero()[0] + 1      # local min
            l_Price_max = (np.diff(np.sign(np.diff(a))) < 0).nonzero()[0] + 1      # local max
                
            ### Ensure both have enough datapoint for judgement
            if len(l_MACD_max) < 2: return NONE
            if len(l_Price_max) < 2: return NONE
            
            # calculate slope to judge direction of slope
            # to double the sign. Note :  index0 is most recent data
            # Bearish Check
            signMACD_Bearish = self.__dictMACDWindow[symbol][l_MACD_max[0]] - self.__dictMACDWindow[symbol][l_MACD_max[1]]
            signPrice_Bearish =  self.__dictPriceWindow[symbol][l_Price_max[0]] - self.__dictPriceWindow[symbol][l_Price_max[1]]
 
            if signMACD_Bearish < 0 and signPrice_Bearish > 0:
                self.Debug("Devergence Bearish signal")
                return SELL
            
            ## Bullish check   
            if len(l_MACD_min) < 2: return NONE
            if len(l_Price_min) < 2: return NONE
                
            signMACD_Bullish = self.__dictMACDWindow[symbol][l_MACD_min[0]] - self.__dictMACDWindow[symbol][l_MACD_min[1]]
            signPrice_Bullish =  self.__dictPriceWindow[symbol][l_Price_min[0]] - self.__dictPriceWindow[symbol][l_Price_min[1]]
            if signMACD_Bullish > 0 and signPrice_Bullish < 0:
                self.Debug("Devergence Bullish signal")
                return BUY
              
            return NONE
                
        
        ## Bolinger Band Indicator
        def Indicator_BB(symbol):
        
            # wait for our Bolinger Band to fully initialize
            if not self.__dictBB[symbol].IsReady: return NONE
        
            holdings = self.Portfolio[symbol].Quantity
            price = self.Securities[symbol].Price
            
            # buy if price above upper bollinger band
            if holdings <= 0:
                 if price > self.__dictBB[symbol].UpperBand.Current.Value:
                    return BUY
            
            # sell if price below Lower bollinger band
            if holdings > 0 and price < self.__dictBB[symbol].LowerBand.Current.Value:
                return SELL
            
            return NONE
                
        ## evaluate all equities buy/sell
        for equity in self.equities:
            # only once per day
            if self.__dictPrev[equity].date() == self.Time.date(): continue

            MACD_BuySell = Indicator_MACD(equity)
            RSI_BuySell = Indicator_RSI(equity)
            BB_BuySell = Indicator_BB(equity)
            
            MACD_Divergence_BuySell = MACDevergence_BuySell(equity)
            
            if MACD_Divergence_BuySell == SELL and MACD_BuySell == BUY:
                self.Debug("Conflict signal : "+ equity)
            elif MACD_Divergence_BuySell == SELL and MACD_BuySell == SELL:
                self.Debug("Matching signal :" + equity)
                
            #long for combination indicators
            #if MACD_BuySell == BUY:
            #if MACD_BuySell == BUY and MACD_Divergence_BuySell != SELL and RSI_BuySell == BUY:
            if MACD_BuySell == BUY and RSI_BuySell == BUY:
            #if MACD_BuySell == BUY and BB_BuySell == BUY:
            #if MACD_BuySell == BUY and RSI_BuySell == BUY and BB_BuySell == BUY:
                # longterm says buy as well
                self.SetHoldings(equity, self.holdRatio)

            # short for combination indicators
            #elif MACD_BuySell == SELL:
            #elif MACD_BuySell == SELL and MACD_Divergence_BuySell != BUY and RSI_BuySell == SELL:
            elif MACD_BuySell == SELL and RSI_BuySell == SELL:
            #elif MACD_BuySell == SELL and BB_BuySell == SELL:
            #elif MACD_BuySell == SELL and RSI_BuySell == SELL and BB_BuySell == SELL:
                self.Liquidate(equity)

            self.__dictPrev[equity] = self.Time
    
                
        # Liquidate if portfolio value low
        if self.Portfolio.TotalPortfolioValue < 0.80 * self.PortfolioValue:
            self.stop = True
            self.Liquidate()
            self.Debug("Liquidate.. Portfolio Cash : " + str(self.Portfolio.Cash))
            self.Notify.Email("netyth@gmail.com", "Account Balance Alert", 
            "Your portfolio balance is less than 80% of the amount you started off with.")