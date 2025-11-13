let questions = [];
let currentIndex = 0;
let score = 0;
let answered = false;
let userAnswers = [];
let totalChoiceQuestions = 0;
let quizTopic = "";
let quizSummary = null;

const API_URL = "https://api.siliconflow.cn/v1/chat/completions";
const API_KEY = "sk-iujgwjycqgmvzxycfgyynuowipaykmbbcneerzvdnehpqvfs";

function generate_QUESTION_TEMPLATE(core_topic) {
  return `# 角色与任务 🎯
你是一位资深的**教育评估专家**和**专业命题人**。你的任务是根据给定的核心主题，生成一套高质量、严谨的测验题。

# 核心主题
我们的课程是大数据分析基础。因此题目与大数据相关。
本套测验的核心主题是：**${core_topic}**

# 质量与严谨性要求 🧐
1.  **专业性**：题目必须反映该主题的核心概念和关键知识点。
2.  **严谨性**：问题表述清晰无歧义，答案唯一且正确。
3.  **迷惑性（选择题）**：错误选项 (Distractors) 必须具有高度的迷惑性，是基于常见误解设计的，而不能是明显无关的选项。

# 数量与格式要求 (【强制】)
请**严格且仅**输出一个符合以下格式的 JSON 对象。**禁止**在 JSON 对象前后添加任何开场白、解释、总结或 Markdown 标记 (如 \`\`\`json ... \`\`\`)。

**数量**：必须包含 **8 个** \`single-choice\` 题目 和 **2 个** \`short-answer\` 题目。

!!!注意fillinblank是简答题而不是填空题。选择题需要给出答案。选择题包含三个字段[question,options,right-answer]。主观题包含一个字段"question"

**JSON 格式**：
{
  "title": "${core_topic}",
  "single-choice": [
    {
      "question": "（这里是第 1 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    },
    {
      "question": "（这里是第 2 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    },
    {
      "question": "（这里是第 3 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    },
    {
      "question": "（这里是第 4 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    },
    {
      "question": "（这里是第 5 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    },
    {
      "question": "（这里是第 6 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    },
    {
      "question": "（这里是第 7 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    },
    {
      "question": "（这里是第 8 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }
  ],
  "short-answer": [
    {
      "question": "（这里是第 1 个简答题）"
    },
    {
      "question": "（这里是第 2 个简答题）"
    }
  ]
}
再次提示：
1.主观题不是填空题，应该是答题者用一段话回答。
2. 选择题必须把答案一起输出在json中。**每一个选择题都应当存在right-answer字段**`;
}

// 从 URL 参数获取主题
function getTopicFromURL() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get("topic") || "大数据分析基础"; // 默认主题
}

// 调用 LLM API 生成题目
async function generateQuestions(topic) {
  const prompt = generate_QUESTION_TEMPLATE(topic);

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "zai-org/GLM-4.5-Air",
        messages: [
          {
            role: "user",
            content: prompt,
          },
        ],
      }),
    });

    if (!response.ok) {
      throw new Error(`API 请求失败: ${response.status}`);
    }

    const data = await response.json();
    const content = data.choices[0].message.content.trim();

    try {
      await fetch("/api/llm-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: prompt }],
          response: data,
          model: "zai-org/GLM-4.5-Air",
          module: "frontend.quizpage",
          metadata: { function: "generateQuestions", topic: topic },
        }),
      });
    } catch (logError) {
      console.error("Failed to log LLM call:", logError);
    }

    let jsonContent = content;

    if (content.startsWith("```json")) {
      jsonContent = content.replace(/```json\s*/, "").replace(/```\s*$/, "");
    } else if (content.startsWith("```")) {
      jsonContent = content.replace(/```\s*/, "").replace(/```\s*$/, "");
    }

    const questionsData = JSON.parse(jsonContent);
    return questionsData;
  } catch (error) {
    console.error("生成题目失败:", error);
    throw error;
  }
}

window.onload = function () {
  loadQuestions();
};

async function loadQuestions() {
  try {
    const topic = getTopicFromURL();
    quizTopic = topic;

    document.querySelector(
      ".json-upload p"
    ).textContent = `正在为主题"${topic}"生成测验题目...`;

    const questionsData = await generateQuestions(topic);

    processQuestions(questionsData);

    startQuiz();
  } catch (error) {
    alert("题目生成失败，请刷新页面重试！");
    console.error("题目生成错误:", error);

    document.querySelector(".json-upload p").textContent =
      "题目生成失败，请刷新页面重试";
    document.getElementById("loadingSpinner").style.display = "none";
  }
}

function processQuestions(jsonData) {
  questions = [];

  if (jsonData["single-choice"]) {
    jsonData["single-choice"].forEach((q) => {
      questions.push({
        type: "choice",
        question: q.question,
        options: q.options,
        answer: q["right-answer"],
      });
    });
    totalChoiceQuestions = jsonData["single-choice"].length;
  }

  if (jsonData["short-answer"]) {
    jsonData["short-answer"].forEach((q) => {
      questions.push({
        type: "text",
        question: q.question,
      });
    });
  }

  document.getElementById("totalQuestions").textContent = questions.length;
}

function startQuiz() {
  document.getElementById("jsonUpload").style.display = "none";
  document.getElementById("progressContainer").style.display = "block";
  currentIndex = 0;
  score = 0;
  answered = false;
  userAnswers = [];
  renderQuestion();
}

function updateProgress() {
  const progress = ((currentIndex + 1) / questions.length) * 100;
  document.getElementById("progressBar").style.width = progress + "%";
  document.getElementById("currentQuestion").textContent = currentIndex + 1;
}

function renderQuestion() {
  const container = document.getElementById("quizContainer");
  const q = questions[currentIndex];
  answered = false;

  let html = `
                          <div class="question-slide active">
                              <div class="question-header">
                                  <span class="question-number">${
                                    q.type === "choice" ? "选择题" : "简答题"
                                  } ${currentIndex + 1}</span>
                                  <span class="question-type">${
                                    q.type === "choice"
                                      ? "单项选择"
                                      : "开放问答"
                                  }</span>
                              </div>
                              <div class="question-text">${q.question}</div>
                      `;

  if (q.type === "choice") {
    html += '<div class="options">';
    q.options.forEach((option, index) => {
      const letter = String.fromCharCode(65 + index);
      html += `<div class="option" onclick="selectOption('${letter}')"><span>${option}</span><span class="option-icon"></span></div>`;
    });
    html += "</div>";
    html += '<div class="feedback" id="feedback"></div>';
  } else {
    html += `
                              <textarea class="text-answer" id="textAnswer" placeholder="请在此输入你的答案..."></textarea>
                              <div class="image-upload-section">
                                  <label for="imageUpload" class="upload-btn">📷 上传图片答案</label>
                                  <input type="file" id="imageUpload" accept="image/*" style="display: none;" onchange="handleImageUpload(event)">
                                  <div id="uploadStatus"></div>
                              </div>
                              <div class="feedback" id="feedback"></div>
                          `;
  }

  html += `
                          <div class="nav-buttons">
                              ${
                                currentIndex > 0
                                  ? '<button class="btn btn-secondary" onclick="previousQuestion()">← 上一题</button>'
                                  : ""
                              }
                              <button class="btn" id="nextBtn" onclick="nextQuestion()" ${
                                q.type === "choice" ? "disabled" : ""
                              }>
                                  ${
                                    currentIndex === questions.length - 1
                                      ? "完成测验 →"
                                      : "下一题 →"
                                  }
                              </button>
                          </div>
                      </div>
                      `;

  container.innerHTML = html;
  updateProgress();
}

function selectOption(selected) {
  if (answered) return;

  const q = questions[currentIndex];
  const options = document.querySelectorAll(".option");
  const feedback = document.getElementById("feedback");
  const nextBtn = document.getElementById("nextBtn");

  options.forEach((opt) => opt.classList.add("disabled"));

  const isCorrect = selected === q.answer;
  userAnswers[currentIndex] = { selected, correct: isCorrect };

  if (isCorrect) {
    score++;
    feedback.className = "feedback correct show";
    feedback.textContent = "✓ 太棒了！回答正确！";
  } else {
    feedback.className = "feedback incorrect show";
    feedback.textContent = `✗ 回答错误。正确答案是：${q.answer}`;
  }

  options.forEach((opt) => {
    const letter = opt.querySelector("span").textContent.charAt(0);
    const icon = opt.querySelector(".option-icon");
    if (letter === q.answer) {
      opt.classList.add("correct");
      icon.textContent = "✓";
    } else if (letter === selected) {
      opt.classList.add("incorrect");
      icon.textContent = "✗";
    }
  });

  answered = true;
  nextBtn.disabled = false;
}

async function evaluateTextAnswer(question, answer) {
  const prompt = `请你作为一个评分老师，评判以下学生的简答题答案。

题目：${question}

学生答案：${answer}

评分标准：
1. 答案是否理解并回答了问题的核心内容
2. 答案是否有实质性的内容（不是空洞或敷衍的回答）
3. 答案的逻辑是否清晰、表达是否连贯
4. 答案是否包含了相关的知识点

如果答案满足以上大部分标准，有一定的质量和深度，请回复"1|优秀的回答！你的答案涵盖了关键要点。"
如果答案基本合理但不够完整或深入，请回复"1|回答正确，但还可以更加深入。"
如果答案明显错误、不相关、过于简单或空洞，请回复"0|回答需要改进。请确保理解题目要求，并提供更具体的内容。"

输出格式：[分数]|[反馈]，其中分数为0或1。`;

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "inclusionAI/Ling-mini-2.0",
        messages: [
          {
            role: "user",
            content: prompt,
          },
        ],
      }),
    });

    const data = await response.json();
    const result = data.choices[0].message.content.trim();

    try {
      await fetch("/api/llm-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: prompt }],
          response: data,
          model: "zai-org/GLM-4.5-Air",
          module: "frontend.quizpage",
          metadata: {
            function: "evaluateTextAnswer",
            question: question,
            answer: answer,
          },
        }),
      });
    } catch (logError) {
      console.error("Failed to log LLM call:", logError);
    }

    const parts = result.split("|");
    const scoreStr = parts[0].trim();
    const feedback = parts.length > 1 ? parts[1].trim() : "已评分";

    const score = scoreStr.includes("1") ? 1 : 0;

    return { score, feedback };
  } catch (error) {
    console.error("LLM评分错误:", error);
    return { score: 1, feedback: "评分系统暂时不可用，已自动给分。" };
  }
}

async function nextQuestion() {
  const q = questions[currentIndex];

  if (q.type === "text") {
    const textAnswer = document.getElementById("textAnswer").value.trim();

    if (!textAnswer) {
      alert("请输入答案后再继续！");
      return;
    }

    const feedback = document.getElementById("feedback");
    const nextBtn = document.getElementById("nextBtn");
    feedback.className = "feedback loading show";
    feedback.innerHTML =
      '<span class="loading-spinner"></span> 正在评分中，请稍候...';
    nextBtn.disabled = true;

    const evalResult = await evaluateTextAnswer(q.question, textAnswer);

    userAnswers[currentIndex] = {
      answer: textAnswer,
      score: evalResult.score,
    };

    if (evalResult.score === 1) {
      score++;
      feedback.className = "feedback correct show";
      feedback.textContent = `✓ ${evalResult.feedback}`;
    } else {
      feedback.className = "feedback incorrect show";
      feedback.textContent = `✗ ${evalResult.feedback}`;
    }

    await new Promise((resolve) => setTimeout(resolve, 2000));
    nextBtn.disabled = false;
  }

  if (currentIndex < questions.length - 1) {
    const slide = document.querySelector(".question-slide");
    slide.classList.remove("active");
    slide.classList.add("exit");

    setTimeout(() => {
      currentIndex++;
      renderQuestion();
    }, 400);
  } else {
    showResults();
  }
}

function previousQuestion() {
  if (currentIndex > 0) {
    const slide = document.querySelector(".question-slide");
    slide.classList.remove("active");
    slide.classList.add("exit");

    setTimeout(() => {
      currentIndex--;
      renderQuestion();
    }, 400);
  }
}

async function handleImageUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const statusDiv = document.getElementById("uploadStatus");
  statusDiv.innerHTML = '<span style="color: #7a6ad8;">正在识别图片...</span>';

  const formData = new FormData();
  formData.append("image", file);

  try {
    const response = await fetch("/api/ocr/extract", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("图片识别失败");
    }

    const data = await response.json();
    const textAnswer = document.getElementById("textAnswer");

    if (textAnswer.value.trim()) {
      textAnswer.value += "\n\n" + data.text;
    } else {
      textAnswer.value = data.text;
    }

    statusDiv.innerHTML = '<span style="color: #10b981;">✓ 图片识别成功</span>';
    setTimeout(() => {
      statusDiv.innerHTML = "";
    }, 3000);
  } catch (error) {
    statusDiv.innerHTML =
      '<span style="color: #ef4444;">✗ 图片识别失败，请重试</span>';
    console.error("OCR Error:", error);
  }
}

async function showResults() {
  document.getElementById("quizContainer").style.display = "none";
  const resultScreen = document.getElementById("resultScreen");
  const finalScore = document.getElementById("finalScore");
  const resultMessage = document.getElementById("resultMessage");
  const resultIcon = document.querySelector(".result-icon");
  const analysisBtn = document.getElementById("analysisBtn");

  finalScore.textContent = `${score}/${questions.length}`;

  let message = "";
  let icon = "🎉";
  const percentage = (score / questions.length) * 100;

  if (percentage >= 90) {
    message = "优秀！你的表现非常出色！";
    icon = "🏆";
  } else if (percentage >= 70) {
    message = "良好！继续保持！";
    icon = "⭐";
  } else if (percentage >= 60) {
    message = "及格！还有进步空间。";
    icon = "👍";
  } else {
    message = "继续努力！不要气馁。";
    icon = "💪";
  }

  resultIcon.textContent = icon;
  resultMessage.innerHTML = `
                          总得分：${score}/${questions.length} 分<br>
                          ${message}<br><br>
                          感谢你完成所有题目！
                      `;

  resultScreen.classList.add("show");
  document.getElementById("progressBar").style.width = "100%";

  generateQuizSummary();

  if (quizTopic && percentage >= 80) {
    try {
      const response = await fetch("/api/quiz/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          node_name: quizTopic,
          score: score,
          total: questions.length,
        }),
      });
      const data = await response.json();
      if (data.success) {
        console.log("✅ Quiz completion recorded");
      }
    } catch (error) {
      console.error("Error recording quiz completion:", error);
    }
  }
}

async function generateQuizSummary() {
  const analysisBtn = document.getElementById("analysisBtn");

  let choiceDetails = "";
  let textDetails = "";

  questions.forEach((q, i) => {
    if (q.type === "choice") {
      const userAns = userAnswers[i];
      if (userAns) {
        choiceDetails += `题目 ${i + 1}: ${q.question}\n`;
        choiceDetails += `学生选择: ${userAns.selected}\n`;
        choiceDetails += `正确答案: ${q.answer}\n`;
        choiceDetails += `结果: ${userAns.correct ? "✓ 正确" : "✗ 错误"}\n\n`;
      }
    } else if (q.type === "text") {
      const userAns = userAnswers[i];
      if (userAns) {
        textDetails += `题目 ${i + 1}: ${q.question}\n`;
        textDetails += `学生答案: ${userAns.answer}\n`;
        textDetails += `得分: ${userAns.score}\n\n`;
      }
    }
  });

  if (!choiceDetails) choiceDetails = "无选择题";
  if (!textDetails) textDetails = "无简答题";

  const prompt = `你是一位专业的教育评估专家。请根据学生的测验结果，生成一份详细的测验总结报告。

请分析以下内容：
1. 学生在选择题中的表现，包括答对的题目和答错的题目
2. 学生选择错误选项的原因分析（是概念混淆、知识点遗漏还是粗心大意）
3. 学生在简答题中的表现和答题质量
4. 针对错误的知识点，给出具体的学习建议

请用中文输出，格式清晰，分点说明。总结应该具有建设性，帮助学生明确自己的薄弱环节。

测验主题：${quizTopic}
总分：${score}/${questions.length}

选择题详情：
${choiceDetails}

简答题详情：
${textDetails}

请生成一份详细的测验总结报告。`;

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "inclusionAI/Ling-mini-2.0",
        messages: [
          {
            role: "user",
            content: prompt,
          },
        ],
      }),
    });

    if (!response.ok) {
      throw new Error(`API 请求失败: ${response.status}`);
    }

    const data = await response.json();
    quizSummary = data.choices[0].message.content.trim();
    analysisBtn.style.display = "inline-block";

    try {
      await fetch("/api/llm-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: prompt }],
          response: data,
          model: "inclusionAI/Ling-mini-2.0",
          module: "frontend.quizpage",
          metadata: {
            function: "generateQuizSummary",
            topic: quizTopic,
            score: `${score}/${questions.length}`,
          },
        }),
      });
    } catch (logError) {
      console.error("Failed to log LLM call:", logError);
    }
  } catch (error) {
    console.error("生成测验总结失败:", error);
  }
}

function showAnalysis() {
  document.getElementById("resultScreen").style.display = "none";
  const analysisScreen = document.getElementById("analysisScreen");
  const analysisContent = document.getElementById("analysisContent");

  if (quizSummary) {
    const renderedMarkdown = marked.parse(quizSummary);
    analysisContent.innerHTML = `<div>${renderedMarkdown}</div>`;
  } else {
    analysisContent.innerHTML =
      '<div style="color: #ef4444; text-align: center;">测验总结生成失败</div>';
  }

  analysisScreen.style.display = "block";
  analysisScreen.classList.add("show");
}

function hideAnalysis() {
  document.getElementById("analysisScreen").style.display = "none";
  document.getElementById("resultScreen").style.display = "block";
}
