import pandas as pd

class find_match:
    instances = {}
    comp_table_2 = None
    def __init__(self, peaks, file):
      self.peak_table = peaks
      find_match.instances[file] = self
      self.peaks = pd.DataFrame(columns = ['Components', 'Start', 'Stop', 'Average Signal'])

    def map(self):
        self.peak_list = []
        peaks_size = self.peak_table.shape[0]
        comp_size = self.comp_table_2.shape[0]
        for i in range(peaks_size):
            rt = self.peak_table.at[i, 'Start']
            for x in range(comp_size):
                if rt >= self.comp_table_2.at[x,'Start-Time'] and rt <= self.comp_table_2.at[x,'End-Time']:   
                    self.peak_list.append([self.comp_table_2.at[x,'Components'], self.peak_table.at[i, 'Start'],
                                                                                self.peak_table.at[i, 'Stop'],
                                                                                self.peak_table.at[i, 'Average Signal']] )    
        self.peaks.drop(self.peaks.index, inplace=True)
        for y in range(len(self.peak_list)):
            self.peaks.loc[y] = self.peak_list[y]
        return self.peaks
       
