import React, { createContext, useContext, useState, useEffect } from 'react';

const LanguageContext = createContext(null);

export const translations = {
  EN: {
    dashboard: 'Dashboard',
    messages: 'Messages',
    startConsultation: 'Start Consultation',
    howItWorks: 'How it Works',
    heroTitle: 'Your Virtual Pharmacist, ',
    heroTitleAccent: 'Always Online.',
    heroSubtitle: 'Get instant medical advice, manage prescriptions, and order medications through our intelligent chat platform. Clinical expertise at your fingertips.',
    trustText: 'patients trust us',
    featuresTitle: 'Complete Pharmaceutical Care',
    featuresSubtitle: 'Modern technology meets clinical excellence to provide you with the most efficient pharmacy experience possible.',
    feature1Title: '24/7 AI Consultation',
    feature1Desc: 'Get instant answers to medication questions and run symptom assessments anytime, day or night.',
    feature2Title: 'Verified Prescriptions',
    feature2Desc: 'Our AI cross-checks every interaction with certified medical databases to ensure total clinical safety.',
    feature3Title: 'Fast Home Delivery',
    feature3Desc: 'Seamless refill processing with door-to-door delivery within hours. Stay home, stay safe.',
    ctaTitle: 'Experience the future of healthcare interaction',
    ctaItem1: 'Privacy-first medical encrypted messaging',
    ctaItem2: 'Direct integration with your local pharmacy',
    ctaItem3: 'Real-time prescription tracking',
    tryAssistant: 'Try AI Assistant',
    readyTitle: 'Ready to simplify your health management?',
    readySubtitle: 'Join thousands of patients who have made MedAgent their trusted medical companion.',
    getStarted: 'Get Started Today',
    talkSpecialist: 'Talk to a Specialist',
    backToHome: 'Back to Home',
    settings: 'Settings',
    support: 'Support',
    profile: 'Profile',
    security: 'Security',
    appearance: 'Appearance',
    chatHistory: 'Chat History',
    activeThreads: 'Active Threads',
    categories: 'Categories',
    searchPlaceholder: 'Search conversations...',
    newConversation: 'New Conversation',
    loading: 'Loading...',
    noHistory: 'No history yet',
    conversationsCount: 'conversations',
    welcomeTitle: 'Hello! I am MedAgent',
    welcomeSubtitle: 'Your AI health assistant. I can help you look up medication info, advise on symptoms, or analyze pharmacy data.',
    disclaimer: 'Information is for medical reference only',
    suggestion1: 'What are the effects of Paracetamol?',
    suggestion2: 'I have a headache and mild fever, what should I do?',
    suggestion3: 'Draw a chart of top 5 best-selling drugs',
    suggestion4: 'How to effectively prevent seasonal flu?',
  },
  VN: {
    dashboard: 'Tổng quan',
    messages: 'Tin nhắn',
    startConsultation: 'Bắt đầu tư vấn',
    howItWorks: 'Cách hoạt động',
    heroTitle: 'Dược sĩ ảo của bạn, ',
    heroTitleAccent: 'Luôn trực tuyến.',
    heroSubtitle: 'Nhận lời khuyên y tế ngay lập tức, quản lý đơn thuốc và đặt thuốc thông qua nền tảng chat thông minh của chúng tôi. Chuyên môn lâm sàng trong tầm tay bạn.',
    trustText: 'bệnh nhân tin tưởng chúng tôi',
    featuresTitle: 'Chăm sóc Dược phẩm Toàn diện',
    featuresSubtitle: 'Công nghệ hiện đại kết hợp với sự xuất sắc trong lâm sàng để mang lại cho bạn trải nghiệm nhà thuốc hiệu quả nhất.',
    feature1Title: 'Tư vấn AI 24/7',
    feature1Desc: 'Nhận câu trả lời ngay lập tức cho các câu hỏi về thuốc và thực hiện đánh giá triệu chứng bất cứ lúc nào, ngày hay đêm.',
    feature2Title: 'Đơn thuốc được Xác thực',
    feature2Desc: 'AI của chúng tôi đối chiếu mọi tương tác với các cơ sở dữ liệu y tế được chứng nhận để đảm bảo an toàn lâm sàng tuyệt đối.',
    feature3Title: 'Giao hàng Nhanh tại Nhà',
    feature3Desc: 'Xử lý nạp thuốc liền mạch với giao hàng tận nhà trong vòng vài giờ. Ở nhà, an toàn.',
    ctaTitle: 'Trải nghiệm tương lai của tương tác chăm sóc sức khỏe',
    ctaItem1: 'Tin nhắn mã hóa y tế ưu tiên quyền riêng tư',
    ctaItem2: 'Tích hợp trực tiếp với nhà thuốc địa phương của bạn',
    ctaItem3: 'Theo dõi đơn thuốc theo thời gian thực',
    tryAssistant: 'Thử Trợ lý AI',
    readyTitle: 'Sẵn sàng đơn giản hóa việc quản lý sức khỏe của bạn?',
    readySubtitle: 'Tham gia cùng hàng ngàn bệnh nhân đã coi MedAgent là người đồng hành y tế đáng tin cậy của họ.',
    getStarted: 'Bắt đầu ngay hôm nay',
    talkSpecialist: 'Nói chuyện với Chuyên gia',
    backToHome: 'Quay lại Trang chủ',
    settings: 'Cài đặt',
    support: 'Hỗ trợ',
    profile: 'Hồ sơ',
    security: 'Bảo mật',
    appearance: 'Giao diện',
    chatHistory: 'Lịch sử trò chuyện',
    activeThreads: 'Luồng hoạt động',
    categories: 'Danh mục',
    searchPlaceholder: 'Tìm kiếm cuộc trò chuyện...',
    newConversation: 'Cuộc trò chuyện mới',
    loading: 'Đang tải...',
    noHistory: 'Chưa có lịch sử',
    conversationsCount: 'cuộc trò chuyện',
    welcomeTitle: 'Xin chào! Tôi là MedAgent',
    welcomeSubtitle: 'Trợ lý sức khỏe AI của bạn. Tôi có thể giúp bạn tra cứu thông tin thuốc, tư vấn triệu chứng hoặc phân tích dữ liệu hiệu thuốc.',
    disclaimer: 'Thông tin chỉ mang tính chất tham khảo y khoa',
    suggestion1: 'Thuốc Paracetamol có tác dụng gì?',
    suggestion2: 'Tôi bị đau đầu và sốt nhẹ, nên làm gì?',
    suggestion3: 'Vẽ biểu đồ top 5 thuốc bán chạy nhất',
    suggestion4: 'Cách phòng ngừa cúm mùa hiệu quả?',
  },
  JP: {
    dashboard: 'ダッシュボード',
    messages: 'メッセージ',
    startConsultation: '相談を開始',
    howItWorks: '仕組み',
    heroTitle: 'あなたのバーチャル薬剤師、',
    heroTitleAccent: 'いつでもオンライン。',
    heroSubtitle: '当社のインテリジェントなチャットプラットフォームを通じて、即座に医療アドバイスを受け、処方箋を管理し、薬を注文できます。臨床の専門知識をあなたの指先で。',
    trustText: 'の患者様が信頼しています',
    featuresTitle: '総合的な医薬品ケア',
    featuresSubtitle: '最新のテクノロジーと優れた臨床技術が融合し、最も効率的な薬局体験を提供します。',
    feature1Title: '24時間365日のAI相談',
    feature1Desc: '昼夜を問わず、薬に関する質問への即座の回答や症状の評価を受けることができます。',
    feature2Title: '検証済みの処方箋',
    feature2Desc: '当社のAIは、認定された医療データベースとのすべての相互作用を相互チェックし、完全な臨床的安全性を確保します。',
    feature3Title: '迅速な自宅配送',
    feature3Desc: '数時間以内のドア・ツー・ドアの配送で、シームレスな薬の補充処理を実現します。自宅で安全に。',
    ctaTitle: 'ヘルスケアインタラクションの未来を体験する',
    ctaItem1: 'プライバシー優先の医療暗号化メッセージング',
    ctaItem2: '地元の薬局との直接的な統合',
    ctaItem3: 'リアルタイムの処方箋追跡',
    tryAssistant: 'AIアシスタントを試す',
    readyTitle: '健康管理を簡素化する準備はできていますか？',
    readySubtitle: 'MedAgentを信頼できる医療パートナーとしている何千人もの患者様に加わりましょう。',
    getStarted: '今日から始める',
    talkSpecialist: '専門家に相談する',
    backToHome: 'ホームに戻る',
    settings: '設定',
    support: 'サポート',
    profile: 'プロフィール',
    security: 'セキュリティ',
    appearance: '外観',
    chatHistory: 'チャット履歴',
    activeThreads: 'アクティブなスレッド',
    categories: 'カテゴリー',
    searchPlaceholder: '会話を検索...',
    newConversation: '新しい会話',
    loading: '読み込み中...',
    noHistory: '履歴はありません',
    conversationsCount: '件の会話',
    welcomeTitle: 'こんにちは！私はMedAgentです',
    welcomeSubtitle: 'あなたのAI健康アシスタントです。薬の情報の検索、症状のアドバイス、薬局データの分析をお手伝いします。',
    disclaimer: '情報は医療上の参照のみを目的としています',
    suggestion1: 'パラセタモールの効果は何ですか？',
    suggestion2: '頭痛と軽い発熱があります。どうすればいいですか？',
    suggestion3: '売れ筋薬トップ5のチャートを作成する',
    suggestion4: '季節性インフルエンザを効果的に予防するには？',
  }
};

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('language') || 'EN';
  });

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  const t = (key) => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
