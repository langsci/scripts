import glob
import re 
import os
import BeautifulSoup
import sys
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mplcolors


class Book():
  def __init__(self, ID, title, colors, shapes):
    seed = hash(str(ID))
    self.ID = int(ID)
    self.title = title 
    self.downloads = {}
    self.color = colors[seed%len(colors)]
    self.shape = shapes[seed%len(shapes)]    
  

  def computeYAggregates(self,labels,threshold):    
    basis = [self.downloads.get(label,0) for label in labels]
    aggregate = [sum(basis[0:i+1]) for i,el in enumerate(basis)]
    #aggregate = [(a if a>threshold else 0) for a in aggregate]    
    aggregate = self.zeros2nones(aggregate)
    self.yaggregates =  aggregate
    print self.ID, self.yaggregates
  
  def zeros2nones(self,a):
    result = []
    for i,e in enumerate(a):
      try:
        if a[i+1]==0:
          result.append(None)
        else:
          result.append(e)
      except IndexError:
          result.append(e)
    return result
          
          
      
  
class Catalog():
  def __init__(self, booksfile='books.tsv'):
    #read ID and title of books from file
    lines = open(booksfile).read().decode('utf8').split('\n') 
    #print lines
    #put ID as key and title as value in dictionary
    #self.books = dict([l.strip().split('\t') for l in lines if l.strip()!='']) 
    #setup colors and shapes to select from
    colors = plt.cm.Set1(np.linspace(0, 1, 45)) 
    #colors = 'bgrcmyk'
    shapes = 'v^osp*D'    
    self.books = {} 
    for l in lines:
      if l.strip()!='':
        ID, title = l.strip().split('\t') 
        ID = int(ID)
        self.books[ID] = Book(ID, title, colors, shapes)
    #collect all directories with access information
    self.dirs = glob.glob('webreport_langsci-press.org_catalog_20[0-9][0-9]_[01][0-9]')
    #extract access data from all log files
    self.monthstats = dict([(d[-7:], Stats(os.path.join(d,'awstats.langsci-press.org.urldetail.html')).getBooks()) for d in self.dirs]) 
    aggregationdictionary = {}
    for bID in self.books:
      aggregationdictionary[int(bID)] = {}   
    #print aggregationdictionary
    for month in self.monthstats: 
      monthfactor = 1 #correctionfactor for incomplete logs
      if month == "2016_05": #in May 2016, only 24/31 days were logged
        monthfactor = 1.3        
      if month == "2016_06": #in June 2016, only 15/30 days were logged
        monthfactor = 2      
      for book in self.monthstats[month]:
        if int(book) in self.books:
          if int(book) == 94 and month == "2016_05": #book 94 was published mid-may, hence the factor is 16/8 and not 31/24
            monthfactor = 2
          try: 
            aggregationdictionary[book][month] = int(self.monthstats[month][book]*monthfactor)
          except KeyError:          
            aggregationdictionary[book][month] = 0     
    aggregationdictionary[52]["2016_06"] = 48 #logging was off in that month
    aggregationdictionary[53]["2016_06"] = 84 #logging was off in that month    
    for bookID in aggregationdictionary:
      self.books[bookID].downloads = aggregationdictionary[bookID]
    
    self.countrystats = dict([(d[-7:],CountryStats(os.path.join(d,'awstats.langsci-press.org.alldomains.html')).getCountries()) for d in self.dirs])   
        
  def setupPlot(self, labels, timeframe):  
    fig = plt.figure()
    #use a wide picture
    fig.set_figwidth(12)
    #fig.add_subplot(ax)
     
    plt.rc('legend',**{'fontsize':9})
    plt.xticks(range(len(labels)+1)[-timeframe:], [l[-5:].replace('_','/') for l in labels[-timeframe:]], fontsize = 10) 
    
    #fig.patch.set_visible(False)
    #ax.axis('off')
    return fig, plt
  
  def matplotcumulative(self,ID=False, legend=True, fontsizetotal=15, threshold=99, timeframe=13):
    """
    produce cumulative graph
    
    Aggregate cumulative data for time sequence.
    Plot this data with matplotlib.
    Also plot all individual books
    """
    
    #sort the keys so we get them in temporal order
    labels = sorted(self.monthstats.keys())    
    #setup matplot 
    fig, plt = self.setupPlot(labels,timeframe)
    ax = plt.subplot(111)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.yaxis.set_ticks_position('left')
    ax.xaxis.set_ticks_position('bottom')
    ax.set_ylabel('downloads')
    ax.set_xlabel('months')   
      
    #displaylimit = timeframe
    origlabels = labels
    
    aggregatedownloads = 0    
    graphs = 0
    for bookID in self.books:
      self.books[bookID].computeYAggregates(labels, threshold)
      
    for bookID in sorted(self.books.keys(), key=lambda k: self.books[k].yaggregates[-1],reverse=True): 
      book = self.books[bookID]
      #compute total download data over all books
      try:
        totaldownloads = book.yaggregates[-1]
        aggregatedownloads +=  totaldownloads
        graphs += 1
      except TypeError: #no download data
        pass
      if book.yaggregates[-1]<30: #make sure no test or bogus data are displayed
        continue            
      xs = range(len(labels)+1)[-timeframe-1:] + [None]
      ys = book.yaggregates[-timeframe-1:] + [None]
      #plot line
      ax.plot(xs, ys, color=book.color, linewidth=1.5) 
      #plot marks
      ax.plot(xs, ys, book.shape, color=book.color, label="(%s) %s" % (ys[-2], book.title[:45])) 
      
    #position legend box
    if legend:
      box = ax.get_position()
      ax.set_position([box.x0, box.y0, box.width * 0.66, box.height]) 
      stretchfactor=25/graphs
      ax.legend(loc='center left', bbox_to_anchor=(1, 0.5),frameon=False,numpoints=1,labelspacing=stretchfactor)     
    #save file
    plt.savefig('cumulativeall.svg')
    plt.savefig('cumulativeall.png')
    plt.close(fig)   
    print "plotted cumulative graph"
    print "total downloads of all books:", aggregatedownloads    
    print "plotting invididual graphs: "
    #individual plots
    for bookID in self.books:
      book = self.books[bookID]
      if book.yaggregates[-1]<30: #only generate graphics for books with sizable downloads
        continue      
      bookfig, bookplt = self.setupPlot(labels,timeframe)      
      bookax = plt.subplot(111)
      bookax.spines['right'].set_visible(False)
      bookax.spines['top'].set_visible(False)
      bookax.yaxis.set_ticks_position('left')
      bookax.xaxis.set_ticks_position('bottom')
      bookax.set_ylabel('downloads')
      bookax.set_xlabel('months')           
      xs = range(len(labels)+1)[-timeframe-1:] + [None]
      ys = book.yaggregates[-timeframe-1:] + [None]
      totaldownloads = book.yaggregates[-1]
      #plot line
      bookax.plot(xs, ys, color=book.color, linewidth=1.5) 
      #plot marks
      bookax.plot(xs, ys, book.shape, color=book.color, label="%s" % (ys[-2])) 
      #add number at end of graph
      bookax.text(len(origlabels), totaldownloads, '      %s'%totaldownloads, fontsize=12)       
      bookplt.savefig('%s.svg'%bookID)
      bookplt.savefig('%s.png'%bookID)
      bookplt.close(fig)    
      print bookID,   
   
  def plotCountries(self,threshold=12):
    """
    Produce a pie chart of downloads per country.
    $threshold countries will be named, the rest
    will be aggregated as "other"
    """
    
    aggregationdictionary = {}
    for month in self.countrystats:
      monthdictionary = self.countrystats[month]
      monthfactor = 1 #correctionfactor for incomplete logs
      if month == "2016_05": #in May 2016, only 24/31 days were logged
        monthfactor = 1.3        
      if month == "2016_06": #in June 2016, only 15/30 days were logged
        monthfactor = 2    
      for country in monthdictionary:
        try:
          aggregationdictionary[country] += int(int(monthdictionary[country].replace(',',''))*monthfactor)
        except KeyError:
          aggregationdictionary[country] = int(int(monthdictionary[country].replace(',',''))*monthfactor)
          
    for k in aggregationdictionary:
      print k, aggregationdictionary[k]
    #get list of countries and downloads
    list_ = [(k,aggregationdictionary[k]) for k in aggregationdictionary]        
    #sort list by number of downloads
    list_.sort(key=lambda x: x[1], reverse=True) 
    #compute values for named countries and "other"
    values = [t[1] for t in list_][:threshold]+[sum([t[1] for t in list_][threshold:])]  
    #set labels for named countries and "other"
    labels = ['%s: %s'%t for t in list_][:threshold]+['Other:%s'%values[-1]]
    #for i in range(threshold+1,len(labels)):
      #labels[i]=''
    print labels, values
    cmap = plt.get_cmap('Paired')
    colors = [cmap(i) for i in np.linspace(0, 1, threshold+1)]
    #setup matplot 
    fig = plt.figure()
    plt.axis("equal") 
    fig.set_figwidth(12)
    ax = plt.subplot(111)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.66, box.height]) 
    plt.pie(values, labels=labels, colors=colors, labeldistance=1.4)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5),frameon=False,numpoints=1) 
    plt.savefig('countries.png') 
    plt.savefig('countries.svg') 
         
class Stats():
  def __init__(self,f):
    """
    navigate the html file to find the relevant <td>s and
    create a dictionary mapping urls to download figures
    """
    
    self.hits = dict(
                      [
                        (
                          #locate key
                          tr.findAll('td')[0].text,
                          #remove thousands separator and convert value to int
                          int(tr.findAll('td')[1].text.replace(',',''))
                        ) 
                        for tr in BeautifulSoup.BeautifulSoup(open(f))\
                                              .find('table',attrs={'class':'aws_data'})\
                                              .findAll('tr')[1:]
                      ]
                  )    


    
  def getBooks(self):
    """
    analyze the access data and aggregate stats for books across publication formats
    """
    
    aggregationdictionary = {}
    for k in self.hits:
      if 'view' in k: #ignore /download/, which is used for files other than pdf
        i=0
        try:
          #extract ID
          i = int(re.search('view/([0-9]+)',k).groups()[0])
        except AttributeError:
          print "no valid book key in %s" %k
          continue
        try:
          #accumulate figures for the various publication formats
          aggregationdictionary[i] += self.hits[k]
        except KeyError:
          aggregationdictionary[i] = self.hits[k]
    return aggregationdictionary
    
        
  def getCountries(self):
    """
    analyze the access data and aggregate stats for countries
    """
    
    aggregationdictionary = {}
    for k in self.hits: 
      try:
        #accumulate figures for the various publication formats
        aggregationdictionary[k] += self.hits[k]
      except KeyError:
        aggregationdictionary[k] = self.hits[k] 
    return aggregationdictionary
   
class CountryStats(Stats):
  def __init__(self,f):
    """
    navigate the html file to find the relevant <td>s and
    create a dictionary mapping urls to download figures
    """		  
    self.hits = dict(
                    [
                      (
                        #locate key
                        tr.findAll('td')[2].text,
                        #remove thousands separator and convert value to int
                        tr.findAll('td')[4].text
                      ) 
                      for tr in BeautifulSoup.BeautifulSoup(open(f))\
                                              .find('table',attrs={'class':'aws_data'})\
                                              .findAll('tr')[1:]
                    ]
                    )  

                    
if __name__=='__main__':
  c = Catalog()
  print "country plot"
  c.plotCountries(threshold=13)
  print 30*'-'  
  print "book plots"
  c.matplotcumulative(fontsizetotal=7)     