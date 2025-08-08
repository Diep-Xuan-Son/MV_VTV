import os
import jwt
import asyncio
from datetime import datetime
from langchain_openai import ChatOpenAI
from base.agent import Agent

from libs.config import Config
from libs.utils import logging, formatter
LOGGER = logging.getLogger("multi_agent")
FILE_HANDLER = logging.FileHandler(f"{Config.PATH_LOG}{os.sep}multi_agent_{datetime.now().strftime('%Y_%m_%d')}.log")
FILE_HANDLER.setFormatter(formatter)
LOGGER.addHandler(FILE_HANDLER)

PROMPT_IDEA = """
Here is the title: {title}

Here is the newspaper: {text}

Give me some brief idea in the newspaper below:
Format output as JSON with pair of value including: "idea_<index>": <content of idea>

## RULES
- Don't repeat title in idea
- Removing the dot after abbreviations in place names
- The response must be in Vietnamese
"""

PROMPT_CLASSIFY_IDEA = """
ID videos and descriptions: {description}

Here is ideas: {ideas}

Based on the descriptions of videos, select one or more appropriate ideas that match with the content of video
Format output as JSON like: 
{{
    <id video>: {{
        <idea index1>: <content of idea>,
        <idea index2>: <content of idea>
    }}
}}

## RULES
- Each idea just appear in one id video
- Focus on the objects in description to select appropriately
- All ideas need to be selected
"""

PROMPT_SYNTHESIS = """
Here is the title video: {title}

ID videos and ideas: {ideas} 

## TASKS
- Based on these ideas of videos, write for me short news for each video
- Sort video for creating an excited news

Format output as JSON like: 
{{
    <id video>: <short news>
}}

## RULES
- The response must be in Vietnamese
- Bold the important information, just bold less than five words
- Remember to sort video
- Each video must have description
- Don't use commas for enumerating will be better
- Just get existed video
- Each sentence is under 20 words
"""
# - Change the comma in numeric to dot, don't change date time
# - Interrupt a sentence using "\\t"
# - Use "\\n" to set a sentence as a new line

PROMPT_REWRITE_ABBREVIATION = """
Here is the id video and their news: {news}

## TASKS
- Rewrite all number and abbreviation of these news 
Format output as JSON like: 
{{
    <id video>: {{<original words>: <new words>}}
}}

## RULES
- The response must be in Vietnamese
- The word like TNHH also is an abbreviation
"""

PROMPT_SPLIT_TITLE = """
Here is the title: {title}
Interrupt the title reasonably with one to three comma
Each splited tittle need to be under 6 words
Don't use comma for single word
Change the comma in numeric to dot, don't change date time
Keep apostrophe or double quote symbol 
Output is a new title
"""
# Bold the important information

class MultiAgent(object):
    def __init__(self, llm: object, ):
        self.idea_agent = Agent(
            system_prompt = "You are an expert in press.",
            prompt = PROMPT_IDEA,
            llm = llm
        )
        self.classify_agent = Agent(
            system_prompt = "You are an expert in press.",
            prompt = PROMPT_CLASSIFY_IDEA,
            llm = llm
        )

        self.synthesis_agent = Agent(
            system_prompt = "You are an excellent reporter.",
            prompt = PROMPT_SYNTHESIS,
            llm = llm
        )

        self.rewrite_abbreviation_agent = Agent(
            system_prompt = "",
            prompt = PROMPT_REWRITE_ABBREVIATION,
            llm = llm
        )

        self.split_title_agent = Agent(
            system_prompt = "",
            prompt = PROMPT_SPLIT_TITLE,
            llm = llm
        )

    async def get_idea(self, text: str, title: str):
        def OutputStructured(BaseModel):
            """Format the response as JSON with keys are 'idea_<index>'"""

        result = await self.idea_agent(OutputStructured, text=text, title=title)
        LOGGER.info(f"----get_idea: {result}")
        return result

    async def select_idea(self, description: dict, ideas: dict):
        def OutputStructured(BaseModel):
            """Format the response as JSON with keys are id videos, and values are pairs of idea index with content of idea"""

        LOGGER.info(description)
        result = await self.classify_agent(OutputStructured, description=description, ideas=ideas)
        LOGGER.info(f"----select_idea: {result}")
        return result

    async def synthesize_idea(self, ideas, title):
        def OutputStructured(BaseModel):
            """Format the response as JSON with keys are id videos, and values are short news"""

        result = await self.synthesis_agent(OutputStructured, ideas=ideas, title=title)
        LOGGER.info(f"----synthesize_idea: {result}")
        return result

    async def rewrite_abbreviation(self, news):
        def OutputStructured(BaseModel):
            """Format the response as JSON with keys are id videos, and values are pairs of abbreviation and new words"""

        result = await self.rewrite_abbreviation_agent(OutputStructured, news=news)
        LOGGER.info(f"----rewrite_abbreviation: {result}")
        return result

    async def split_title(self, title):
        def OutputStructured(BaseModel):
            """Format the response as JSON with key is 'result'"""

        result = await self.split_title_agent(OutputStructured, title=title)
        LOGGER.info(f"----split_title: {result}")
        return result

if __name__=="__main__":
    SECRET_KEY     = os.getenv('SECRET_KEY', "MMV")
    token_openai   = os.getenv('API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5Ijoic2stcHJvai1QSDNHNnlMVEticmdvaU9ieTA4YlVMNHc0eVYxR3NJa25IeEltTl9VMFI1WmVsOWpKcDI0MzZuNUEwOTdVdTVDeXVFMDJha1RqNVQzQmxia0ZKX3dJTUw2RHVrZzh4eWtsUXdsMTN0b2JfcGVkV1c0T1hsNzhQWGVIcDhOLW1DNjY1ZE1CdUlLMFVlWEt1bzRRUnk2Ylk1dDNYSUEifQ.2qjUENU0rafI6syRlTfnKIsm6O4zuhHRqahUcculn8E')
    api_key_openai = jwt.decode(token_openai, SECRET_KEY, algorithms=["HS256"])["api_key"]

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=api_key_openai,  # if you prefer to pass api key in directly instaed of using env vars
        # base_url="...",
        # organization="...",
        # other params...,
        streaming=True
    )

    # text = "Trong số hơn 800 loại trà đến từ 36 quốc gia và vùng lãnh thổ có mặt tại Pháp cũng có tên trà của Việt Nam. Bất ngờ hơn nữa, trong đó có hai loại là trà ô long ướp hoa sen và trà xanh ướp hoa sen được thương hiệu Mariage Frères nổi tiếng xếp vào dòng sản phẩm cao cấp nhất, với giá bán hơn 1.000 euro/ký. Ở Kẻ Chợ - tên gọi dân gian chung của kinh thành Thăng Long vào thế kỷ 17 - có một khu vực dành cho các công ty và doanh nhân nước ngoài. Sớm nhất là thương điếm của Công ty Đông Ấn Hà Lan được mở vào năm 1637, tiếp đến là thương điếm của Công ty Đông Ấn Anh được lập vào năm 1863, sau đó đến các nước khác. Trà Việt Nam có lẽ đã bắt đầu được xuất khẩu sang phương Tây thông qua các công ty của Hà Lan và Anh này. Mức tăng trưởng của ngành trà ngày càng cao do lối sống thay đổi và người tiêu dùng nhận thức cao về việc uống trà có lợi cho sức khỏe. Vào danh mục trà cao cấp với giá bán hơn 1.000 euro mỗi ký Theo báo cáo của Guillaume Capus, chuyến hàng trà Đông Dương đầu tiên xuất khẩu sang Pháp là vào năm 1893. Năm 1899, trà Đông Dương được bán tại Paris (Pháp) và một số nước châu Âu, tổng khối lượng xuất khẩu là 131.391 ký, sau đó tăng lên mức 180.000 ký vào năm 1900. Trong số hơn 800 loại trà đến từ 36 quốc gia và vùng lãnh thổ hiện có mặt tại Pháp cũng có tên trà của Việt Nam. Bất ngờ hơn nữa, trong đó có hai loại là trà oolong ướp hoa sen và trà xanh ướp hoa sen được thương hiệu Mariage Frères nổi tiếng xếp vào dòng sản phẩm cao cấp nhất, với giá bán hơn 1.000 euro/ký. Người đưa được trà Việt Nam lên kệ của Mariage Frères là ông Thân Dỹ Ngữ, Giám đốc Công ty TNHH Hiệp Thành - doanh nghiệp sản xuất nông sản hữu cơ, chuyên xuất khẩu trà và nông sản hữu cơ sang thị trường Liên minh châu Âu và Mỹ. Ông cũng là thành viên Hiệp hội Nông nghiệp hữu cơ Việt Nam; là một trong những người sáng lập Liên minh Trà đặc sản hữu cơ Việt Nam (VOSTEA). Trà ướp hoa sen là một trong những sản phẩm đặc sắc nhất của trà Việt Nam. Ảnh: Đỗ Quang Tuấn Hoàng Năm 2011, ông Ngữ quyết định tiếp cận thị trường châu Âu khi Nhà máy trà hữu cơ Bản Liền (huyện Bắc Hà, tỉnh Lào Cai) đã đạt công suất 10 tấn/năm. Thời điểm năm 2000 khi ông Ngữ bắt đầu xuất khẩu trà thì thị trường Tây Âu mua khoảng 10.000 tấn trà/năm. Đó là loại trà búp (leaf grade) - một là loại trà ngon, trong ngành gọi là OP. Ở thời điểm hiện nay, thị trường Tây Âu vẫn nhập khoảng 7.000-10.000 tấn trà Việt Nam mỗi năm, nhưng chủ yếu là trà vụn (broken), tức là họ đang mua loại trà giá rẻ để làm trà túi lọc. Khách châu Âu, Mỹ - những khách hàng cao cấp - đã từng mua trà Việt Nam nhưng vì nhiều lý do, như họ nhận được hàng không đúng mẫu, hay chất lượng kém đi, hoặc lo ngại dư lượng thuốc bảo vệ thực vật trong trà… đã mất niềm tin vào trà Việt Nam. Khi bán cho Mariage Frères, ông Ngữ mới biết là họ đã nghiên cứu thị trường Việt Nam từ rất lâu rồi. Họ làm việc rất kỹ lưỡng và phối hợp với các phòng thí nghiệm lớn chuyên nghiên cứu các đặc sản vùng miền ở khắp nơi trên thế giới. Công nghệ hiện nay cho phép đưa thực phẩm vào máy và đo được ngay định tính để truy xuất nguồn gốc, biết được sản phẩm có lỗi gì, ví dụ như trà lên men không đạt thì sẽ không thấy xuất hiện một số chất có lợi cho sức khỏe hoặc có những chất có hại khác… “Thế nên khi chúng tôi đưa được trà (ướp hoa) sen và một số loại trà khác vào được Mariage Frères thì tôi nghĩ chúng tôi đã thành công. Nhưng số lượng thì vẫn không được nhiều”, ông Ngữ chia sẻ. Dựng lại niềm tin Để quảng bá trà Việt Nam, ông Thân Dỹ Ngữ đã làm việc với các chuyên gia thử nếm trà như Lydia Gautier, Carine Baudry…, gửi mẫu trà tham dự Cuộc thi Trà quốc tế hàng năm của AVPA (Agence pour la Valorisation des Produits Agricoles: Hiệp hội Nâng cao giá trị nông sản Pháp). Ông gửi các sản phẩm trà từ vùng Chiêu Lầu Thi (huyện Hoàng Su Phì, tỉnh Hà Giang) gồm trà tiên, trà móng rồng (Camellia crassicolumna), hồng trà shan tuyết cổ thụ (Camellia sinensis var. Shan). Các sản phẩm trà đó đã đoạt cả giải vàng, giải bạc. Ông Ngữ tiếp tục giới thiệu cho Hiệp hội Chè Việt Nam và nhiều nhà sản xuất trà ở Việt Nam gửi mẫu tham dự Cuộc thi Trà quốc tế hàng năm của AVPA nhằm quảng bá các vùng trà khác của Việt Nam. Theo ông Ngữ, việc đoạt giải quốc tế với trà Việt Nam không khó vì trà của nước ta có chất lượng tốt không thua kém bất cứ nước, nào dù vậy vẫn còn nhiều việc doanh nghiệp xuất khẩu trà phải lưu tâm. Bản thân ông đang tập trung vào việc phát triển chuỗi để cung cấp được hàng liền mạch. Theo ông, một là phải khả thi về mặt chế biến. Hai là giá thành phải hợp lý. Có như vậy trà mới vào được các chuỗi cung ứng. Theo ước tính, Việt Nam hiện có khoảng 120.000 héc ta diện tích trồng trà, có 257 doanh nghiệp chế biến trà quy mô công nghiệp, tổng công suất theo thiết kế 5.200 tấn búp tươi/ngày. Ngành trà đặt mục tiêu mở rộng diện tích trồng đến năm 2030 ở mức 135.000-140.000 héc ta; đến năm 2025 này diện tích trà được chứng nhận an toàn lên đến 55% và đến năm 2030 là khoảng 75%. Tuy nhiên, số nhà máy chế biến trà được trang bị đồng bộ, máy móc thiết bị tốt, bảo đảm các tiêu chuẩn kỹ thuật hiện chỉ chiếm 20%; số nhà máy có công nghệ chế biến tạm đạt yêu cầu kỹ thuật là 60%; số cơ sở chế biến chắp vá, không bảo đảm các yêu cầu kỹ thuật của quá trình chế biến trà là 20%. Nghiên cứu do Research and Markets công bố, thị trường trà toàn cầu dự kiến sẽ đạt 37,5 tỉ đô la Mỹ trong năm 2025. Mức tăng trưởng của ngành trà ngày càng cao do lối sống thay đổi và người tiêu dùng nhận thức cao về việc uống trà có lợi cho sức khỏe. Sản phẩm trà cũng có nhiều thay đổi để phù hợp với cuộc sống. Theo đó, trà cao cấp uống tại nhà, trà ướp hoa, trà ủ lạnh, kombucha… được dự báo sẽ là những dòng sản phẩm dẫn dắt thị trường trong giai đoạn tới. Vùng trà shan tuyết Bản Liền (huyện Bắc Hà, tỉnh Lào Cai) mà ông Thân Dỹ Ngữ đưa sản phẩm sang thị trường Paris năm 2011 nay đã thay da đổi thịt. Toàn huyện Bắc Hà hiện có 950 héc ta trà, trong đó gần 700 héc ta trà shan hữu cơ, tạo việc làm và thu nhập thường xuyên cho trên 300 hộ dân với hơn 1.500 người tại bốn thôn người Tày. Trà shan tuyết Bản Liền là sản phẩm OCOP 5 sao đầu tiên của tỉnh Lào Cai tìm được chỗ đứng ở thị trường Mỹ và châu Âu. Từ hơn 100 thành viên ban đầu, đến nay hợp tác xã đã có hơn 300 hộ liên kết trồng trà và bán trà búp tươi cho hợp tác xã. Hợp tác xã đang sản xuất hơn 10 loại trà, giá thấp nhất là trà xanh 700.000 đồng/ký, đắt nhất là trà ướp hoa sen, giá 5 triệu đồng/ký. Đây là một trong những thành viên của Liên minh Trà đặc sản hữu cơ Việt Nam (VOSTEA) mà ông Thân Dỹ Ngữ góp sức sáng lập. Theo ông Hoàng Vĩnh Long, Chủ tịch Hiệp hội Chè Việt Nam, ngành trà cần phải đầu tư có trọng điểm vào công tác chế biến sâu, đặc biệt là các sản phẩm trà sau chế biến có chất lượng cao, mang lại giá trị kinh tế lớn để hình thành ngành công nghiệp chế biến trà tiên tiến tại Việt Nam; đa dạng hóa sản phẩm trà chế biến bằng công nghệ tiên tiến."
    MA = MultiAgent(llm)
    # MA.get_idea(text=text)
    # exit()

    ideas = {'idea_1': 'Hai loại trà ô long ướp hoa sen và trà xanh ướp hoa sen của Việt Nam đã được thương hiệu Mariage Frères xếp vào dòng sản phẩm cao cấp nhất, với giá bán hơn 1.000 euro/ký.', 'idea_2': 'Trà Việt Nam bắt đầu được xuất khẩu sang phương Tây từ thế kỷ 17 thông qua các công ty Đông Ấn Hà Lan và Anh.', 'idea_3': 'Ngành trà Việt Nam đang tăng trưởng nhờ lối sống thay đổi và nhận thức cao về lợi ích sức khỏe của việc uống trà.', 'idea_4': 'Ông Thân Dỹ Ngữ, Giám đốc Công ty TNHH Hiệp Thành, là người đưa trà Việt Nam vào kệ của Mariage Frères và đã thành công trong việc quảng bá trà Việt Nam ra thế giới.', 'idea_5': 'Việt Nam hiện có khoảng 120.000 héc ta diện tích trồng trà và mục tiêu mở rộng lên 135.000-140.000 héc ta vào năm 2030.'}

    description = {'video_0': 'Hình ảnh cận cảnh một tách trà Việt Nam màu hổ phách, được đựng trong chén sứ trắng vẽ hình ảnh đậm chất Á Đông. Bọt trà li ti nổi trên bề mặt, tạo cảm giác tươi mới và hấp dẫn. Sự kết hợp giữa màu sắc và họa tiết mang đến vẻ đẹp tinh tế, gợi nhớ đến văn hóa trà đạo truyền thống.', 'video_1': 'Bức ảnh thể hiện một khung cảnh thanh bình với hai người, một người đàn ông lớn tuổi và một người phụ nữ trẻ, đang thưởng trà theo phong cách truyền thống Việt Nam. Bộ trà cụ tinh xảo và trang phục truyền thống làm tăng thêm vẻ đẹp và sự trang trọng của buổi trà đạo. Sự tương phản giữa thế hệ và sự kết nối với văn hóa tạo nên một hình ảnh hấp dẫn.', 'video_2': 'Hình ảnh cận cảnh của trà Việt Nam, có thể là một loại trà đặc biệt như trà Shan Tuyết cổ thụ, với những búp trà xanh và những sợi trắng (có thể là tuyết trà hoặc một loại nấm cộng sinh). Hình ảnh này gợi lên sự quý hiếm và chất lượng cao của trà.'}

    ideas = {'idea_1': 'Future Homes đã khai trương chi nhánh mới tại Đà Nẵng vào ngày 2/7/2025, nhằm mở rộng sự hiện diện tại miền Trung.', 'idea_2': 'Đà Nẵng được chọn làm địa điểm chi nhánh mới nhờ vào vai trò là trung tâm kinh tế, du lịch và công nghệ của khu vực miền Trung – Tây Nguyên.', 'idea_3': 'Chi nhánh Đà Nẵng nằm ở vị trí trung tâm, gần các đầu mối giao thông quan trọng, thuận tiện cho giao dịch và tổ chức sự kiện.', 'idea_4': 'Văn phòng mới sẽ phân phối các dự án bất động sản cao cấp từ nhiều chủ đầu tư lớn như Masterise Homes, BRG Group và Vinhomes.', 'idea_5': 'Future Homes đang phát triển đội ngũ môi giới chuyên nghiệp và sử dụng công nghệ hiện đại để tối ưu hóa trải nghiệm khách hàng.', 'idea_6': 'Doanh nghiệp đã triển khai nền tảng CRM tích hợp AI để hỗ trợ mô hình dịch vụ tư vấn theo định hướng đầu tư.', 'idea_7': 'Lễ khai trương có sự tham gia của ban lãnh đạo công ty, các đối tác và nhân sự từ Hà Nội và Đà Nẵng, khẳng định cam kết mở rộng hệ sinh thái bất động sản.'}
    description = {'video_0': 'Hình ảnh ghi lại khoảnh khắc khai trương chi nhánh mới của Future Homes tại Đà Nẵng. Bức ảnh có sự tham gia của đông đảo nhân viên và đối tác, tạo nên không khí trang trọng và phấn khởi. Sự kiện này đánh dấu bước phát triển quan trọng của Future Homes trong việc mở rộng thị trường tại khu vực miền Trung.', 'video_1': "Hình ảnh ghi lại khoảnh khắc khai trương chi nhánh Future Homes tại Đà Nẵng. Bảng hiệu lớn màu đỏ nổi bật với dòng chữ 'GRAND OPENING' màu vàng kim, cùng với hình ảnh thành phố Đà Nẵng phía dưới, tạo nên sự trang trọng và thu hút."}

    # asyncio.run(MA.select_idea(description=description, ideas=ideas))
    # exit()

    # img_list_des = {'video_0': {'idea_1': 'Hai loại trà ô long ướp hoa sen và trà xanh ướp hoa sen của Việt Nam đã được thương hiệu Mariage Frères xếp vào dòng sản phẩm cao cấp nhất, với giá bán hơn 1.000 euro/ký.', 'idea_3': 'Ngành trà Việt Nam đang tăng trưởng nhờ lối sống thay đổi và nhận thức cao về lợi ích sức khỏe của việc uống trà.'}, 'video_1': {'idea_2': 'Trà Việt Nam bắt đầu được xuất khẩu sang phương Tây từ thế kỷ 17 thông qua các công ty Đông Ấn Hà Lan và Anh.', 'idea_4': 'Ông Thân Dỹ Ngữ, Giám đốc Công ty TNHH Hiệp Thành, là người đưa trà Việt Nam vào kệ của Mariage Frères và đã thành công trong việc quảng bá trà Việt Nam ra thế giới.'}, 'video_2': {'idea_5': 'Việt Nam hiện có khoảng 120.000 héc ta diện tích trồng trà và mục tiêu mở rộng lên 135.000-140.000 héc ta vào năm 2030.'}}
    # img_list_des = {'video_0': {'idea_1': 'Các quỹ phòng hộ đã đồng loạt bán tháo cổ phiếu năng lượng với tốc độ nhanh nhất kể từ tháng 9/2024 do giá dầu lao dốc.', 'idea_2': 'Giá dầu thô đã giảm hơn 10 USD trong một tuần sau thỏa thuận ngừng bắn giữa Israel và Iran, gây áp lực lên thị trường năng lượng.'}, 'video_1': {'idea_3': 'Xu hướng rút vốn khỏi cổ phiếu năng lượng mạnh mẽ hơn ở châu Âu, nơi các quỹ không chỉ cắt giảm vị thế mua mà còn gia tăng bán khống.', 'idea_4': 'Mặc dù có đợt bán tháo cổ phiếu năng lượng, các quỹ vẫn mua cổ phiếu mạnh nhất trong 5 tuần qua, chuyển hướng đầu tư sang các ngành tài chính, công nghệ và công nghiệp.'}}
    img_list_des = {'video_0': {'idea_1': 'Giá vàng thế giới tăng mạnh, đạt 2.324 USD/ounce, tăng hơn 20 USD/ounce so với đầu phiên, phục hồi sau những phiên giảm trước đó.', 'idea_3': 'Giá vàng trong nước cũng tăng mạnh, với giá vàng miếng SJC tăng khoảng 1 triệu đồng/lượng so với buổi sáng, đạt 75,98 triệu đồng/lượng (mua vào) và 77,98 triệu đồng/lượng (bán ra).', 'idea_4': 'Tập đoàn DOJI cũng điều chỉnh giá vàng SJC lên 75,9 triệu đồng/lượng (mua vào) và 77,9 triệu đồng/lượng (bán ra).'}}
    # img_list_des = {'video_0': {'idea_1': 'Tín dụng tại TP. Hồ Chí Minh đã đạt 4,102 triệu tỉ đồng, tăng 3,89% so với cuối năm 2024, cho thấy sự phục hồi mạnh mẽ của nền kinh tế.', 'idea_2': 'Tốc độ tăng trưởng tín dụng trong 5 tháng đầu năm 2025 cao gấp đôi so với cùng kỳ năm 2023 và 2024, nhờ vào môi trường kinh doanh thuận lợi và chính sách tiền tệ linh hoạt.', 'idea_3': 'Dư nợ tín dụng trong lĩnh vực bán buôn, bán lẻ và sửa chữa ô tô, xe máy đã tăng 15,1% so với cùng kỳ năm trước, cho thấy sự phục hồi trong tiêu dùng.', 'idea_4': 'Ngành công nghiệp chế biến, chế tạo cũng ghi nhận mức tăng trưởng tín dụng đáng kể, cho thấy hoạt động sản xuất đang phục hồi và doanh nghiệp mở rộng đầu tư.', 'idea_5': 'Các yếu tố hỗ trợ tăng trưởng tín dụng bao gồm hoạt động du lịch sôi động và việc giải ngân vốn đầu tư công được thúc đẩy.'}}
    # asyncio.run(MA.synthesize_idea(ideas=img_list_des, title="Tín dụng tại TP. Hồ Chí Minh, vượt mốc 4.1 triệu tỉ đồng, phản ánh đà phục hồi mạnh mẽ, của nền kinh tế"))
    # exit()

    llm1 = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=api_key_openai,  # if you prefer to pass api key in directly instaed of using env vars
        # base_url="...",
        # organization="...",
        # other params...,
        streaming=True
    )
    MA1 = MultiAgent(llm1)
    
    img_des = {'video_1': '**Trà Việt Nam** đã bắt đầu được **xuất khẩu sang phương Tây** từ thế kỷ 17. Ông **Thân Dỹ Ngữ**, Giám đốc Công ty TNHH Hiệp Thành, đã thành công trong việc **quảng bá trà Việt Nam** ra thế giới.', 'video_0': 'Hai loại **trà ô long ướp hoa sen** và **trà xanh ướp hoa sen** của Việt Nam được thương hiệu **Mariage Frères** xếp vào dòng sản phẩm **cao cấp nhất**. Giá bán lên tới **hơn 1.000 euro/ký**. Ngành trà Việt Nam đang **tăng trưởng** nhờ lối sống thay đổi và nhận thức cao về **lợi ích sức khỏe** của việc uống trà.', 'video_2': 'Việt Nam hiện có khoảng **120.000 héc ta** diện tích trồng trà. Mục tiêu mở rộng lên **135.000-140.000 héc ta** vào năm 2030.'}

    # MA1.rewrite_abbreviation(news=img_des)

    # title = f"Thị trường sáng 12/6: 'VN-Index' vượt mốc 1.320 điểm nhờ dòng tiền lan tỏa mạnh mẽ"
    title = "Future Homes khai trương chi nhánh tại Đà Nẵng, mở rộng hiện diện tại thị trường miền Trung"

    asyncio.run(MA1.split_title(title=title))