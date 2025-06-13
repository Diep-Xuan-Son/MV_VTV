from PIL import ImageFont
import re as regex


title = "**Giá vàng SJC**, tiếp tục lập đỉnh, tiến sát mốc **119 triệu đồng/lượng**"

w_title = 345
h_title = 120

sub_title_original = title.split(", ")

sub_title = regex.sub(r'[\*\*.]', '', title).split(", ")
h_sub_title = h_title/len(sub_title)

sub_title_content = []
sub_title_idx = []
[(sub_title_content.append(v), sub_title_idx.append(i)) for i, v in sorted(enumerate(sub_title), key=lambda x: len(x[1]), reverse=True)]
# sub_title = sorted(sub_title, key=len, reverse=True)
print(sub_title_idx)

max_idex_no_changed = len(sub_title)
idx_fz = {}
for idx, stl in zip(sub_title_idx, sub_title_content):
	# for i in sorted(list(idx_fz), reverse=True):
	# 	if idx > i:
	# 		idx_fz[idx] = idx_fz[i]
	# 		break
	if idx in idx_fz:
		# h_sub_title = (h_title-idx_fz[idx][1])/(len(sub_title)-len(idx_fz)+10e-5)
		continue
	font_sz = 30
	font = ImageFont.truetype(f'./font/dejavu-sans/DejaVuSans.ttf', size=font_sz)
	length_stitle = font.getlength(stl)
	height_stitle = sum(font.getmetrics())
	# print(stl)
	# print(height_stitle)
	# print(length_stitle)

	if length_stitle > w_title or height_stitle > h_sub_title:
		for fz in reversed(range(18,30)):
			font = ImageFont.truetype(f'./font/dejavu-sans/DejaVuSans.ttf', size=fz)
			length_stitle = font.getlength(stl)
			height_stitle = sum(font.getmetrics())
			if length_stitle < w_title and height_stitle < h_sub_title:
				break
		# print(font.size)
		# print(height_stitle)
		# print(length_stitle)

	elif length_stitle < w_title and height_stitle < h_sub_title:
		for fz in range(31,40):
			font = ImageFont.truetype(f'./font/dejavu-sans/DejaVuSans.ttf', size=fz)
			length_stitle = font.getlength(stl)
			height_stitle = sum(font.getmetrics())
			if length_stitle > w_title or height_stitle > h_sub_title:
				break
	# 	print(font.size)
	# 	print(height_stitle)
	# 	print(length_stitle)
	# print("---------")
	for i in range(idx, max_idex_no_changed):
		idx_fz[i] = [font.size, height_stitle]
		h_title -= height_stitle
		h_sub_title = h_title/(len(sub_title)-len(idx_fz)+10e-5)

		# idx_fz[i] = idx_fz[idx]
		# h_sub_title = (h_title-idx_fz[i][1])/(len(sub_title)-len(idx_fz)+10e-5)
	max_idex_no_changed = idx
print(idx_fz)

sub_title_fz = dict(zip(sub_title_original, dict(sorted(idx_fz.items())).values()))
print(sub_title_fz)
list_subtile = []
list_bold = []
for stl, fz in sub_title_fz.items():
	bold_text = regex.findall(r'\*\*(.*?)\*\*', stl)
	normal_texts = []
	bold_flag = []
	print(bold_text)
	if bold_text:
		pattern = "|".join(map(regex.escape, bold_text))
		normal_texts = regex.split(pattern, regex.sub(r'[\*\*.]', '', stl))
		print(normal_texts)
		bold_flag = [0]*len(normal_texts)
		i = 1
		for bt in bold_text:
			normal_texts.insert(i, bt)
			bold_flag.insert(i,1)
			i += 2
	else:
		normal_texts.append(stl)
		bold_flag = [0]*len(normal_texts)

	[(normal_texts.pop(j), bold_flag.pop(j)) for j, t in enumerate(normal_texts) if not t]

	list_subtile.append(normal_texts)
	list_bold.append(bold_flag)

print(list_subtile)
print(list_bold)