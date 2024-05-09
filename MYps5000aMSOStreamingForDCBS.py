"""
ps5000_function.py
==================
A function for using picoscope 5000 series
Created on 2024-03-28 by Ayumu Ishijima
"""
#%%
from MYps5000_function import *
myplot()
# Define sample data
sample_period_us = 1
total_time_sec = 0.01
trig_pos = 1 # 40%

chandle, status = ps5000_initialize(sample_period_us, total_time_sec, trig_pos)
adc2mVChAMax,adc2mVChBMax,d0,d1,time = ps5000_acquire(chandle, status,sample_period_us, total_time_sec, trig_pos)
plt.plot(time, adc2mVChAMax,'-*')
plt.plot(time, adc2mVChBMax)
plt.plot(time,d0*1000)
plt.plot(time, d1*1000)
plt.xlabel('Time (us)')
plt.ylabel('Voltage (mV)')
plt.grid()
plt.show()

ps5000_close(chandle, status)
# %%
# Calculate the difference between consecutive elements in d0
d0_diff = np.diff(d0)
# Find the indices where the difference is not zero (i.e., the value changed)
change_indices = np.where(d0_diff != 0)[0]

print(change_indices)
# %%
m = 0
n = 0
d0_off = []
d0_on = []
w_d0_on = []
wo_d0_on = []
d1_off = []
d1_on = []
w_d1_on = []
wo_d1_on = []
chA_on = []
w_chA_on = []
wo_chA_on = []
chB_on = []
w_chB_on = []
wo_chB_on = []

#d0が1となる区間をonとして抽出．d0はトリガー信号かつ積分範囲を決定するゲート信号．これにより信号を抽出する．
#現状はトリガー信号とゲート信号は同一としているが，トリガー信号とゲート信号は分けた方が良いかもしれない．
for i in range(len(change_indices)-1):
    if i % 2 == 0:
        n+= 1
        d0_on.append(d0[change_indices[i]:change_indices[i+1]])
        d1_on.append(d1[change_indices[i]:change_indices[i+1]])
        chA_on.append(adc2mVChAMax[change_indices[i]:change_indices[i+1]])
        chB_on.append(adc2mVChBMax[change_indices[i]:change_indices[i+1]])
    else:
        m+= 1
        d0_off.append(d0[change_indices[i]:change_indices[i+1]])
        d1_off.append(d0[change_indices[i]:change_indices[i+1]])

#w pumpかどうかをd1の平均値で判定し，分類する．
for i in range(len(d0_on)):
    if np.mean(d1_on[i]) > 0.5:
        n+= 1
        w_d0_on.append(d0_on[i])
        w_d1_on.append(d1_on[i])
        w_chA_on.append(chA_on[i])
        w_chB_on.append(chB_on[i])
    else:
        m+= 1
        wo_d0_on.append(d0_on[i])
        wo_d1_on.append(d1_on[i])
        wo_chA_on.append(chA_on[i])
        wo_chB_on.append(chB_on[i])

# %%
plt.plot(w_chA_on[(1)])
plt.show()
wo_d0_on_means = [np.mean(item) for item in wo_d0_on]
w_d0_on_means = [np.mean(item) for item in w_d0_on]
print(wo_d0_on_means)
print(w_d0_on_means)

# %%
d0[change_indices[0]:change_indices[1]]
d0[change_indices[2]:change_indices[3]]

