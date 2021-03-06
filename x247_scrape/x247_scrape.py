import pandas as pd
from bs4 import BeautifulSoup
import requests
import re
import os
import calendar
import time

x247_folder_path = 'x247_scrape\\csv\\'

header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/22.0.1216.0 Safari/537.2'}
          
pos_group_df = pd.read_csv(x247_folder_path + '247_pos_group.csv', header = 0)

def team_info_247_scrape():
    try:
        team_info_df = pd.read_csv(x247_folder_path + '247_team_info.csv', header = 0)
        
        modified_time = os.path.getmtime(x247_folder_path + '247_team_info.csv')
        current_time = calendar.timegm(time.gmtime())
        if float(current_time - modified_time)/(60*60*24) > 365:
            pass
        else:
            return team_info_df
    except:
        pass
    
    team_info_df = pd.DataFrame(columns = ['team_fullname','team_href','team_hrefname'])
    
    abbrv_re = re.compile('((?<=\/\/).*(?=\.247))|((?<=college\/).*)')
        
    url = 'https://247sports.com/league/NCAA-FB/Teams'
    req = requests.get(url, headers = header)
    soup = BeautifulSoup(req.content, 'lxml')
    
    confs = soup.find_all('li', {'class': 'team-block_itm'})
    for conf in confs:
        for team in conf.contents[1].contents[3:]:
            if team != ' ':
                name = team.contents[1].text
                if name == 'Virginia Military Institute Keydets':
                    name = 'VMI Keydets'
                
                href = team.contents[1].get('href')
                if href == '//247sports.com':
                    continue
                href_name = href if abbrv_re.search(href) == None else abbrv_re.search(href).group(0)
                if href not in team_info_df['team_href']:
                    team_info_df.loc[len(team_info_df)] = [name,'https:' + href,href_name]
                                     
    team_info_df.to_csv(x247_folder_path + '247_team_info.csv', index = False)
    return team_info_df
    
def recruits_page_check(min_season, latest_class):
    try:
        page_check_df = pd.read_csv(x247_folder_path + '247_page_check.csv', header = 0)
        sracped_seasons = list(page_check_df['season'].drop_duplicates())
        
        necessary_seasons = []
        for season in range(min_season - 4, latest_class + 1):
            if season not in sracped_seasons:
                necessary_seasons.append(season)
                
        if necessary_seasons == []:
            return page_check_df
    except:
        page_check_df = pd.DataFrame(columns = ['season','instgroup','max_page'])
        necessary_seasons = range(min_season - 4, latest_class + 1)
    
    page_check_re = re.compile('(?<=\()[0-9]*(?=\))')
    for season in necessary_seasons:
        for instgroup in ['HighSchool','JuniorCollege','PrepSchool']:
            page_check_url = 'https://247sports.com/Season/' + str(season) + '-Football/CompositeRecruitRankings?InstitutionGroup=' + instgroup
            page_check_req = requests.get(page_check_url, headers = header)
            page_check_soup = BeautifulSoup(page_check_req.content, 'lxml').find('section', {'class': 'list-page'})
            
            max_page = int(page_check_re.search(page_check_soup.contents[1].text).group(0))/50 + (1 if 2157%50 > 0 else 0)
            
            page_check_df.loc[len(page_check_df)] = [season,instgroup,max_page]
                              
    page_check_df.drop_duplicates().to_csv(x247_folder_path + '247_page_check.csv', index = False)
    return page_check_df.drop_duplicates()
     

def recruits_247_scrape(min_season, current_date):
    try:
        recruits_df = pd.read_csv(x247_folder_path + '247_recruits.csv', header = 0)
    except:
        recruits_df = pd.DataFrame(columns = ['season','instgroup','page','recruit_name','recruit_href','team_schoolname','team_href',
                                              'pos','rating','stars','num_services','height','weight','city','state','high_school'])

    latest_class = current_date[0] - (1 if (current_date[1] < 3) else 0)
    page_check_df = recruits_page_check(min_season, latest_class)
    
    href_re = re.compile('.*(?=\/Season)')
    remove_char = '([\\t\'\.\,]+)|([^\x00-\x7F]+)| (i+(v*)$|(j|s)r)'
    
    for season in range(min_season - 4, latest_class + 1):
        for instgroup in ['HighSchool','JuniorCollege','PrepSchool']:
            max_page = page_check_df.loc[(page_check_df['season'] == season)
                & (page_check_df['instgroup'] == instgroup),'max_page'].iloc[0]
            for page in range(1,int(max_page) + 1):
                if page not in list(recruits_df.loc[(recruits_df['season'] == season)
                                    & (recruits_df['instgroup'] == instgroup),'page'].drop_duplicates()):
                    if instgroup == 'PrepSchool':
                        url = 'https://247sports.com/Season/' + str(season) + '-Football/CompositeRecruitRankings?InstitutionGroup=PrepSchool'
                    else:
                        url = 'https://247sports.com/Season/' + str(season) + '-Football/CompositeRecruitRankings?ViewPath=~%2FViews%2F247Sports%2FPlayerSportRanking%2F_SimpleSetForSeason.ascx&InstitutionGroup=' + instgroup + '&Page=' + str(page)
                    req = requests.get(url, headers = header)
                    soup = BeautifulSoup(req.content, 'lxml').find('section', {'id': 'page-content'})
                    
                    recruits = soup.contents
                    if len(recruits) < 2:
                        break
                    else:
                        for recruit in recruits:
                            if recruit == ' ':
                                continue
                            elif recruit.contents[1].get('data-js') == 'showmore':
                                continue
                            elif recruit.contents[1].get('class')[0] != 'dfp_ad':
                                name = re.sub(remove_char,'',recruit.contents[6].contents[1].contents[1].text.lower())
                                
                                if name in [' ','']:
                                    continue
                                try:
                                    college = recruit.contents[8].contents[1].contents[0].get('title')
                                    college_href = href_re.search(recruit.contents[8].contents[1].get('href')).group(0)
                                except:
                                    continue
                                href = recruit.contents[6].contents[1].contents[1].get('href')
                                origin = re.sub(r'[^\x00-\x7F]+','',recruit.contents[6].contents[1].contents[3].text.strip())
                                paren = origin.count('(')
                                school = origin.split(' (')[0]
                                try:
                                    city = origin.split(' (')[paren].split(', ')[0]
                                    state = origin.split(' (')[paren].split(', ')[1][:-1]
                                except:
                                    city,state = None,None
                                pos = recruit.contents[6].contents[3].contents[1].text
                                ht = recruit.contents[6].contents[3].contents[3].text
                                ht = None if (ht[0] not in ['5','6']) else int(ht[0])*12 + float(ht.split('-')[1])
                                
                                wt = recruit.contents[6].contents[3].contents[5].text
                                rate = recruit.contents[6].contents[5].contents[7].text
                                stars = len(recruit.contents[6].contents[5].find_all('span', {'class': 'icon-starsolid yellow'}))
                                rct_srvs = len(recruit.contents[6].contents[5].contents[9].find_all('span', {'class': 'yellow'}))
                                
                            recruits_df.loc[len(recruits_df)] = [season,instgroup,page,name,href,college,college_href,pos,rate,stars,
                                                                rct_srvs,ht,wt,city,state,school]
                                                                
    recruits_df['pos_group'] = pd.merge(recruits_df[['pos']], pos_group_df, how = 'left', on = 'pos')['pos_group']
    recruits_df.drop_duplicates().to_csv(x247_folder_path + '247_recruits.csv', index = False)
    return recruits_df.drop_duplicates()