import requests
from bs4 import BeautifulSoup
import pandas as pd
from abstractscraper import AbstractScraper
import os, time, timeit, re, enum, datetime, multiprocessing


class ChartColumns(enum.Enum):
    sales_price_chart = ['Date', 'Sale Price']
    forecast_model = ['Date', 'Price', 'Product Status']
    listings_monthly_chart = ['Date', 'Lowest Listing Price', 
                        'Price (25th Percentile)', 'Price (75th Percentile)', 'Highest Listing Price']
    sales_trends_chart = ['Date', 'Sales Quantity'] 


class BrickeconScraper(AbstractScraper):
    
    
    def __init__(self):
        super()
        os.chdir("brickecon")
    

    #Retrieves breadcrumbs in pages (example: 4 Juniors (Theme) -> City (Subtheme) -> Advanced Motors (Product))
    def get_breadcrumbs(self, html):
        soup = BeautifulSoup(html, "lxml")
        breadcrumb = soup.find('ol', {"class":"breadcrumb"}) 
        if breadcrumb is None:
            print(soup, html.name)
        else:
            breadcrumb_parts = breadcrumb.find_all('li')
            file_structure = []
            for breadcrumb in breadcrumb_parts:
                file_structure.append(breadcrumb.get_text())
            return file_structure

    #Crawls starting from the brickecononmy sitemap and digs to subtheme pages and finally individual product pages. 
    #In each step, saves html of the page and parses urls to next deeper stage/pages 
    #(ex: In 2nd step, save subtheme page then parses the urls to product pages in the subtheme page)
    def extract(self):
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'}
        base_url = "https://www.brickeconomy.com"

        #Retrieve urls to subtheme pages
        def get_subthemes():
            soup = BeautifulSoup(open("pages\\sitemap.html"), "html.parser")
            themes_html = soup.find_all("div", {"class": "col-md-4 themewrap"})
            subtheme_urls = []
            for html in themes_html:
                #no subthemes in theme. If so, Get theme instead of subthemes
                url_htmls = html.find_all('div')
                if (len(url_htmls) == 1):
                    theme = url_htmls[0]
                    subtheme_urls.append(f"{base_url}{theme.find('a').get('href')}")
                #subthemes present in theme
                else: 
                    for url_html in (url_htmls[1:]):
                        subtheme_urls.append(f"{base_url}{url_html.find('a').get('href')}")
            return subtheme_urls


        #Take urls and saves their webpages' html
        def urls_to_html_products(urls, start_dir, start_index):

            for url in urls[start_index:]:
                request_success = False
                sleep_time = 4
                while not request_success:
                    #If error, pause program for incrementally longer times.
                    #This ensures what we are doing does not constitute a DDOS/bot attack
                    try:
                        sleep_time *= 2
                        r = requests.get(url, headers=headers)
                        request_success = True
                    except:
                        print(urls.index(url))
                        time.sleep(sleep_time)
                        if sleep_time > 32:
                            print(url)
                            quit()

                if r.status_code == 200:
                    html_text = r.text
                else:
                    print("Aborting... HTTP Request was not successful")
                try:
                    file_structure = self.get_breadcrumbs(html_text)
                except AttributeError:
                    continue
                
                os.chdir(start_dir) #./pages for subtheme pages, ./pages/products for product pages.
                try:
                    for level in file_structure[:-1]:
                        if not (level in os.listdir()):
                            os.mkdir(level)
                        os.chdir(level)
                    

                    filename = file_structure[-1] + ".html"
                    if ("/" in filename or "?" in filename):
                        filename = filename.replace("/", "-")
                        filename = filename.replace("?", "")
                    
                    if not (filename in os.listdir()):
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(html_text)
                except:
                    print(urls.index(url))
                    continue
                #Wait for a few seconds to prevent blocking.
                time.sleep(2)
                print(urls.index(url))

        
        #Takes files from page directories and returns a list of all the html files of subthemes 
        def get_subthemes_html():

            all_files = []
            def get_products_html_helper(product_type):
                files = []
                os.chdir(f"C:\\Users\\nutfe\\Desktop\\Programming\\bark\\bark_scrape\\brickecon\\pages\\{product_type}")
                dirs = os.listdir()
                files_in_dir = set()
                for dir in dirs:
                    if os.path.isfile(dir):
                        files.append(open(dir))
                    else:
                        os.chdir(dir)
                        html_lists = [f"{dir}\{html}" for html in os.listdir()] 
                        files_in_dir.update(set(html_lists))
                    os.chdir(f"C:\\Users\\nutfe\\Desktop\\Programming\\bark\\bark_scrape\\brickecon\\pages\\{product_type}")
                files += [open(file) for file in files_in_dir]
                return files

            #Books
            all_files += get_products_html_helper("Books")
            #Sets
            all_files += get_products_html_helper("Sets")
            #Minifigs
            all_files += get_products_html_helper("Minifigs")

            return all_files


        #Take html of subtheme pages and parses the urls to their products' pages
        def get_product_urls(files):
            product_urls = set()
            for file in files:
                try:
                    soup = BeautifulSoup(file, "lxml")
                except FileNotFoundError:
                    print(f"Error: File ({file}) not found")
                    continue

                #minifigs and sets have different table classes.
                product_list = soup.find('table', {"class":f"table table-hover ctlsets-table"})
                if (product_list is None):
                    product_list = soup.find('table', {"class":f"table table-hover ctlminifigs-table"})
                try:
                    product_html = product_list.find_all('h4')
                except:
                    print(file)
                for html in product_html:
                    page_url = html.find('a').get('href')
                    page_url = base_url + page_url
                    product_urls.add(page_url)
            print(len(product_urls))
            return product_urls

        subthemes_html = get_subthemes_html()
        product_urls = get_product_urls(subthemes_html)
        urls_to_html_products(list(product_urls), 
                                "C:\\Users\\nutfe\\Desktop\\Programming\\bark\\bark_scrape\\brickecon\\pages\\products", 
                                18775)

    
    #Takes html of product pages and parses details of products. Saves details in a dict.
    #Returns a list of the dicts of details.
    def transform(self, num_product_start=0, num_product_stop=1000):

        def get_chart_data(file):

            #Determine charts present in product page.
            def get_available_charts(soup):
                chart_section = soup.find('div', {'class':'col-md-8'})
                #Each element stores a list of columns for each chart available in the product page.
                charts_columns_selections = []
                #Checks if it is a sales scatter plot and not a forecast model. If so, it will be true, else false.
                chart_headers_with_tags = chart_section.find_all('h4')
                chart_headers_text = ''
                for chart_header in chart_headers_with_tags:
                    chart_headers_text += (chart_header.text)
                #Price chart
                price_chart_header_set = 'Set Value'
                price_chart_header_minifig = 'Minifig Value'
                if price_chart_header_set in chart_headers_text or price_chart_header_minifig in chart_headers_text:
                    charts_columns_selections.append(ChartColumns.sales_price_chart)
                #Forecast model
                forecast_model_header = 'Forecast Model'
                if forecast_model_header in chart_headers_text:
                    print('found')
                    charts_columns_selections.append(ChartColumns.forecast_model)
                #Monthly listings chart or Listings Chart
                listings_monthly_chart = soup.find('div', id='saleschartmonth')
                sales_trends_chart_unretired = soup.find('div', {'class':'mb-20'}, id='saleschart')
                #Monthly charts for retired products does not have a header/title
                if not sales_trends_chart_unretired is None or not listings_monthly_chart is None:
                    print('true')
                    charts_columns_selections.append(ChartColumns.listings_monthly_chart) #True if there is monthly sales chart
                #Sales trend (quantity sold) chart
                sales_trends_chart_retired = soup.find('div', id='saleschart')
                sale_trend_header_retired = "Sale Trends"
                if sale_trend_header_retired in chart_headers_text and not sales_trends_chart_retired is None:
                    charts_columns_selections.append(ChartColumns.sales_trends_chart) #True if there is sales trend chart
                print(charts_columns_selections)
                return charts_columns_selections

            def parse_chart_data(soup, charts_columns_selections):
                #Each type of chart has different data columns.
                script = soup.select_one("#LoginModal > script")
                chart_datas_dirty = re.findall("data.*\.addRows\(\[\s\s.*", script.text) #Separates charts
                product_charts = {}
                chart_order = 0
                for chart_data_dirty in chart_datas_dirty:
                    chart_data_dirty_values_only = re.findall("\[new Date\(.*\][\,\]]", chart_data_dirty) #Separates the messy data into individual data values.
                    chart_clean = chart_data_dirty_values_only[0]
                    chart_data = []
                    values = re.split("\]\,\s?\[", chart_clean)
                    #A few listing charts are actually sale distribution charts in the product page, which are not included in the list
                    #since data for this type (distribution charts) cannot be extracted.
                    current_chart = charts_columns_selections[chart_order]               
                    chart_columns = current_chart.value
                    chart_name = current_chart.name
                    try:
                        for value in values:
                            data_values = re.findall("[0-9\.?]+", value)
                            year = int(data_values.pop(0))
                            #Some date values confusingly have dates of (XXXX-12-XX). Doesn't modify it if so
                            month = int(data_values.pop(0))
                            if month < 12:
                                month += 1 # add by 1 as months in original extracted data are zero-based (January : 0 -> January : 1) with a few exceptions
                            day = int(data_values.pop(0))
                            #Data has incorrect data with dates being able to be February 29 (including non-leap years). Corrects this to end of month
                            if month == 2 and day > 28:
                                day = 28
                            date = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
                            data_values.insert(0, date)
                            data = {}
                            for column in chart_columns:
                                data[column] = (data_values.pop(0))
                            chart_data.append(data)
                        chart_order += 1
                    except IndexError:
                        print('Wrong chart columns. Moving onto next group of data')
                        continue 
                    chart_df = pd.DataFrame(chart_data, columns=chart_columns)
                    product_charts[chart_name] = chart_df
                return product_charts

            soup = BeautifulSoup(open(file, encoding='utf-8'), "lxml")
            charts_columns_selection = get_available_charts(soup)
            return parse_chart_data(soup, charts_columns_selection)
        
        #Retrieve all files from products directory, including those inside subdirectories.
        def retrieve_product_files():
            os.chdir("C:\\Users\\nutfe\\Desktop\\Programming\\bark\\bark_scrape\\brickecon\\pages\\products")
            product_files = []
            for root_dir, _, files in os.walk('C:\\Users\\nutfe\\Desktop\\Programming\\bark\\bark_scrape\\brickecon\\pages\\products'):
                files = [f"{root_dir}\{file}" for file in files] 
                product_files += files
            return product_files
        
        start = timeit.default_timer()
        details_dicts = []
        charts_data_list = {}
        product_files = retrieve_product_files()
        for product_filename in product_files[num_product_start:num_product_stop]:
            with open(product_filename, encoding="utf-8") as f:
                try:
                    breadcrumbs = self.get_breadcrumbs(f)
                    theme = breadcrumbs[0]
                except:
                    print(f.name)
                    print('File likely has not been downloaded properly')
                    continue
            
            soup = BeautifulSoup(open(product_filename, encoding="utf-8"), "lxml")
            if not (theme == 'Books'):
                details = soup.find('div', id='SetDetails')
                #if minifigs, parse soup html again differently
                if details is None:
                    details = soup.find('div', {'class':'side-box mt-30'})
                product_details = details.find_all('div', {"class":"row rowlist"})
            else:
                continue
            
            details_dict = {}
            #Set details
            for product_detail in product_details:
                row_texts = list(product_detail.strings)
                try:
                    col_name = row_texts[0]
                    col_value = row_texts[1].split('&')[0]
                    details_dict[col_name] = col_value
                except IndexError:
                    continue
            #Removes special characters from 'Pieces' field
            if details_dict.__contains__('Pieces'):
                details_dict['Pieces'] = details_dict['Pieces'].replace(u'\xa0', '')

            #Price details
            price_details = soup.find('div', id="ContentPlaceHolder1_PanelSetPricing")
            #if minifigs, parse soup html again differently
            if price_details is None:
                price_details = soup.find('div', id='ContentPlaceHolder1_PanelMinifigPricing')
            try:
                price_details = price_details.find_all('div', {"class":"row rowlist"})
            except AttributeError:
                print(product_filename)
                continue
            
            try:
                for price_detail in price_details:
                    row_texts = list(price_detail.strings)
                    try:
                        #Makes distinction duplicate values in used condition (only price details of new condition).
                        #Adds used prefix to used values
                        if row_texts[0] in details_dict:
                            row_texts[0] += "_used"
                        details_dict[row_texts[0]] = row_texts[1]
                    except IndexError:
                        continue
            except TypeError:
                print(product_filename)
                continue

            if details_dict.__contains__('Future growth'):
                details_dict['Future growth'] = details_dict['Future growth'].replace(u'\xa0', '')

            details_dicts.append(details_dict)
            charts_data_list[product_filename] = get_chart_data(product_filename)

        stop = timeit.default_timer()
        print(f"Program executed in {stop-start}")
        return details_dicts, charts_data_list
            
    #Converts the list of dicts and saves the data as a csv file.
    def load(self, details_dicts, charts_data_list):
        #general products spreadsheet
        cols = ['Set number', 'Name', 'Theme', 'Subtheme', 'Year', 'Availability', 'Pieces', 'Minifigs', 
                'Retail price', 'Value', 'Value_used', 'Growth', 'Future growth', 'Range', 'Range_used']
        df = pd.DataFrame(details_dicts, columns=cols)
        df.fillna('NA', inplace=True)
        df.to_csv("C:\\Users\\nutfe\\Desktop\\Programming\\bark\\bark_scrape\\brickecon\\data\\products.csv")
        count = 0
        #individual product charts
        for filename, charts_dict in charts_data_list.items():
            print(count)
            count += 1
            print(charts_dict)
            os.chdir("C:\\Users\\nutfe\\Desktop\\Programming\\bark\\bark_scrape\\brickecon\\data_json")
            filename = filename.replace("pages", "data_json")
            dirs_path = filename.split("data_json\\")[1]
            dirs = dirs_path.split("\\")
            for dir in dirs:
                if not (dir in os.listdir()):
                    os.mkdir(dir)
                os.chdir(dir)
            for chart_name, chart_dataframe in charts_dict.items():
                with open(f'{chart_name}.json', 'w', encoding='utf-8') as f:
                    chart_dataframe.to_json(f, orient='records')

    def transform_and_load(self, num_start, num_stop):
        details_dicts, charts_data_list = self.transform(num_start, num_stop)
        self.load(details_dicts, charts_data_list)

    def parallel_transform_and_load(self, batch_size):
        num_cpu = multiprocessing.cpu_count()
        processes = []

        for process_index in range(num_cpu):
            num_product_start = process_index * batch_size
            num_product_stop = num_product_start + batch_size
            process = multiprocessing.Process(target=self.transform_and_load, args=(num_product_start, num_product_stop))
            processes.append(process)
        
        for process in processes:
            process.start()

            
            






