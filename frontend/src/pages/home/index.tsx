import {
  ApartmentOutlined,
  BookOutlined,
  CheckCircleOutlined,
  DeploymentUnitOutlined,
  FilterOutlined,
  ReadOutlined,
  TagsOutlined,
} from "@ant-design/icons";
import { Card, Col, Empty, Row, Segmented, Space, Tag, Typography } from "antd";
import { useMemo, useState } from "react";

import { usePageHashScroll } from "@/app/use-page-hash-scroll";

type OverviewMode = "positioning" | "definitions";
type SubjectKey = "math" | "physics";
type StageKey = "primary" | "junior" | "senior";

type DefinitionBlock = {
  title: string;
  body: string;
  source: string;
};

type DefinitionDataset = {
  headline: string;
  summary: string;
  sections: Array<{
    title: string;
    blocks: DefinitionBlock[];
  }>;
  sourceNote: string;
};

const SHARED_COMPETENCY_LEVEL_BLOCKS: DefinitionBlock[] = [
  {
    title: "水平一",
    body:
      "适用于各核心素养的入门层级。通常表现为：能够在熟悉的情境中识别对象、理解概念或规则，处理简单问题；能够借助学过的方法、模型或图形进行直接分析、表达和求解；在交流中能够解释基本含义，说明简单结论。",
    source: "",
  },
  {
    title: "水平二",
    body:
      "适用于各核心素养的进阶层级。通常表现为：能够在有关联的情境中发现并提出数学问题，理解相关概念、规则、条件与结构之间的联系；能够选择并运用恰当的方法、模型、图形或运算策略解决问题，形成较完整的论证、建模或分析过程；在交流中能够围绕主题清楚表达观点。",
    source: "",
  },
  {
    title: "水平三",
    body:
      "适用于各核心素养的综合层级。通常表现为：能够在综合情境中主动选择研究对象，提出并转化数学问题；能够综合运用数学语言、推理、模型、图形、运算或统计知识，创造性地分析和解决较复杂问题；能够更准确地揭示对象本质，形成新命题、新联系或更高层次的理解，并用于解释现实或跨学科现象。",
    source: "",
  },
];

const modeOptions = [
  { label: "系统定位", value: "positioning" },
  { label: "打标定义", value: "definitions" },
] satisfies { label: string; value: OverviewMode }[];

const subjectOptions = [
  { label: "数学", value: "math" },
  { label: "物理", value: "physics" },
] satisfies { label: string; value: SubjectKey }[];

const stageOptions = [
  { label: "小学", value: "primary" },
  { label: "初中", value: "junior" },
  { label: "高中", value: "senior" },
] satisfies { label: string; value: StageKey }[];

const positioningCards = [
  {
    title: "项目定位",
    value: "K12 学科题目标注底座",
    icon: <ApartmentOutlined />,
    description: "面向题目级数据治理，统一承接导入、筛选、标注、复核和结果沉淀。",
  },
  {
    title: "标注对象",
    value: "学科 / 学段 / 题目",
    icon: <TagsOutlined />,
    description: "以单题为单位，结合题干、作答方式、难度与上下文辅助信息进行判断。",
  },
  {
    title: "当前重点",
    value: "核心素养 + 素养层级",
    icon: <CheckCircleOutlined />,
    description: "当前优先围绕题目所体现的核心素养及其强弱层级建立统一口径。",
  },
  {
    title: "后续扩展",
    value: "知识点 + 认知要求",
    icon: <DeploymentUnitOutlined />,
    description: "后续继续补齐知识点、认知要求与不同学科标准体系的协同展示。",
  },
];

const annotationDimensions = [
  {
    title: "核心素养",
    status: "当前重点",
    description: "判断题目主要依赖哪些学科核心素养完成求解，是能力意图的核心标签。",
  },
  {
    title: "核心素养层级",
    status: "当前重点",
    description: "判断某项素养在该题中的作用强弱，区分辅助出现、关键支撑与核心驱动。",
  },
  {
    title: "知识点",
    status: "后续扩展",
    description: "用于归档题目所属内容结构；若上游已有稳定结果，可避免重复打标。",
  },
  {
    title: "认知要求",
    status: "后续扩展",
    description: "用于描述题目对思维加工深度的要求，但首页仅展示能从标准文件直接确认的内容。",
  },
];

const workflowSteps = [
  "先确定学科与学段，再进入对应课程标准语境。",
  "结合题干、作答方式、题型与难度，判断题目真正依赖的核心素养。",
  "对命中的素养给出层级判断，避免“出现了就算高层级”的过标。",
  "只展示和沉淀有明确标准依据的定义内容，暂不写工作性补充解释。",
];

const strictSourceNotes = [
  {
    title: "义务教育数学",
    detail: "来源文件：小学初中义务教育数学.pdf。当前内容依据课标截图整理，整体定义做简述，具体素养内涵按原文完整保留。",
    fileName: "小学初中义务教育数学.pdf",
  },
  {
    title: "普通高中数学",
    detail: "来源文件：普通高中数学课程标准（2017年版 2020年修订）.pdf。可直接读取并引用六项核心素养与学业质量水平。",
    fileName: "普通高中数学课程标准（2017年版2020年修订）.pdf",
  },
];

const datasetMap: Partial<Record<`${SubjectKey}:${StageKey}`, DefinitionDataset>> = {
  "math:primary": {
    headline: "义务教育数学（小学）",
    summary:
      "义务教育数学课程以核心素养为导向，强调学生在数学学习中逐步形成面向未来发展所需的关键能力。整体上可概括为：会用数学的眼光观察现实世界，会用数学的思维思考现实世界，会用数学的语言表达现实世界。小学阶段侧重对经验的感悟。",
    sections: [
      {
        title: "核心素养整体说明",
        blocks: [
          {
            title: "会用数学的眼光观察现实世界",
            body:
              "通过数学的眼光，可以从现实世界的客观现象中发现数量关系与空间形式，提出有意义的数学问题；能够抽象出数学的研究对象及其属性，形成概念、关系与结构；能够理解自然现象背后的数学原理，感悟数学的审美价值，形成对数学的好奇心与想象力，主动参与数学探究活动，发展创新意识。",
            source: "课标第 12 页",
          },
          {
            title: "会用数学的思维思考现实世界",
            body:
              "通过数学的思维，可以揭示客观事物的本质属性，建立数学对象之间、数学与现实世界之间的逻辑联系；能够根据已知事实或原理，合乎逻辑地推出结论，构建数学的逻辑体系；能够运用符号运算、形式推理等数学方法，分析、解决数学问题和实际问题。",
            source: "课标第 13 页",
          },
          {
            title: "会用数学的语言表达现实世界",
            body:
              "通过数学的语言，可以简约、精确地描述自然现象、科学情境和日常生活中的数量关系与空间形式；能够在现实生活与其他学科中构建普适的数学模型，表达和解决问题；能够理解数据的意义与价值，会用数据的分析结果解释和预测不确定现象，形成合理的判断或决策。",
            source: "课标第 13-14 页",
          },
          {
            title: "小学阶段主要表现",
            body:
              "小学阶段，核心素养主要表现为：数感、量感、符号意识、运算能力、几何直观、空间观念、推理意识、数据意识、模型意识、应用意识、创新意识。",
            source: "课标第 14 页",
          },
        ],
      },
      {
        title: "核心素养主要表现及其内涵",
        blocks: [
          {
            title: "数感",
            body:
              "数感主要是指对于数与数量、数量关系及运算结果的直观感悟。能够在真实情境中理解数的意义，能用数表示物体的个数或事物的顺序；能在简单的真实情境中进行合理估算，作出合理判断；能初步体会并表达事物蕴含的简单数量规律。数感是形成抽象能力的经验基础。建立数感有助于理解数的意义和数量关系，初步感受数学表达的简洁与精确，增强好奇心，培养学习数学的兴趣。",
            source: "表 1，小学",
          },
          {
            title: "量感",
            body:
              "量感主要是指对事物的可测量属性及大小关系的直观感知。知道度量的意义，能够理解统一度量单位的必要性；会针对真实情境选择合适的度量单位进行度量，会在同一度量方法下进行不同单位的换算；初步感知度量工具和方法引起的误差，能合理得到或估计度量的结果。建立量感有助于养成用定量的方法认识和解决问题的习惯，是形成抽象能力和应用意识的经验基础。",
            source: "表 1，小学",
          },
          {
            title: "符号意识",
            body:
              "符号意识主要是指能够感悟符号的数学功能。知道符号表达的现实意义；能够初步运用符号表示数量、关系和一般规律；知道用符号表达的运算规律和推理结论具有一般性；初步体会符号的使用是数学表达和数学思考的重要形式。符号意识是形成抽象能力和推理能力的经验基础。",
            source: "表 1，小学",
          },
          {
            title: "运算能力",
            body:
              "运算能力主要是指根据法则和运算律进行正确运算的能力。能够明晰运算的对象和意义，理解算法与算理之间的关系；能够理解运算的问题，选择合理简洁的运算策略解决问题；能够通过运算促进数学推理能力的发展。运算能力有助于形成规范化思考问题的品质，养成一丝不苟、严谨求实的科学态度。",
            source: "表 1，小学与初中",
          },
          {
            title: "几何直观",
            body:
              "几何直观主要是指运用图表描述和分析问题的意识与习惯。能够感知各种几何图形及其组成元素，依据图形的特征进行分类；根据语言描述画出相应的图形，分析图形的性质，建立形与数的联系，构建数学问题的直观模型；利用图表分析实际情境与数学问题，探索解决问题的思路。几何直观有助于把握问题的本质，明晰思维的路径。",
            source: "表 1，小学与初中",
          },
          {
            title: "空间观念",
            body:
              "空间观念主要是指对空间物体或图形的形状、大小及位置关系的认识。能够根据物体特征抽象出几何图形，根据几何图形想象其所描述的实际物体；想象并表达物体的空间方位和相互之间的位置关系；感知并描述图形的运动和变化规律。空间观念有助于理解现实生活中空间物体的形态与结构，是形成空间想象力的经验基础。",
            source: "表 1，小学与初中",
          },
          {
            title: "推理意识",
            body:
              "推理意识主要是指对逻辑推理过程及其意义的初步感悟。知道可以从一些事实和命题出发，依据规则推出其他命题或结论；能够通过简单的归纳或类比，猜想或发现一些初步的结论；通过法则运用，体验数学从一般到特殊的论证过程；对自己及他人的问题解决过程给出合理解释。推理意识有助于养成讲道理、有条理的思维习惯，增强交流能力，是形成推理能力的经验基础。",
            source: "表 1，小学",
          },
          {
            title: "数据意识",
            body:
              "数据意识主要是指对数据的意义和随机性的感悟。知道在现实生活中，有许多问题应当先做调查研究，收集数据，感悟数据蕴含的信息；知道同样的事情每次收集到的数据可能不同，而只要有足够的数据就可能从中发现规律；知道同一组数据可以用不同方式表达，需要根据问题的背景选择合适的方式。形成数据意识有助于理解生活中的随机现象，逐步养成用数据说话的习惯。",
            source: "表 1，小学",
          },
          {
            title: "模型意识",
            body:
              "模型意识主要是指对数学模型普适性的初步感悟。知道数学模型可以用来解决一类问题，是数学应用的基本途径；能够认识到现实生活中大量的问题都与数学有关，有意识地用数学的概念与方法予以解释。模型意识有助于开展跨学科主题学习，增强对数学的应用意识，是形成模型观念的经验基础。",
            source: "表 1，小学",
          },
          {
            title: "应用意识",
            body:
              "应用意识主要是指有意识地利用数学的概念、原理和方法解释现实世界中的现象与规律，解决现实世界中的问题。能够感知生活中蕴含着大量的与数量和图形有关的问题，可以用数学的方法予以解决；初步了解数学作为一种通用的科学语言在其他学科中的应用，通过跨学科主题学习建立不同学科之间的联系。应用意识有助于用学过的知识和方法解决简单的实际问题，养成理论联系实际的习惯，发展实践能力。",
            source: "表 1，小学与初中",
          },
          {
            title: "创新意识",
            body:
              "创新意识主要是指主动尝试从日常生活、自然现象或科学情境中发现和提出有意义的数学问题。初步学会通过具体的实例，运用归纳和类比发现数学关系与规律，提出数学命题与猜想，并加以验证；勇于探索一些开放性的、非常规的实际问题与数学问题。创新意识有助于形成独立思考、敢于质疑的科学态度与理性精神。",
            source: "表 1，小学与初中",
          },
        ],
      },
      {
        title: "核心素养水平",
        blocks: SHARED_COMPETENCY_LEVEL_BLOCKS,
      },
    ],
    sourceNote:
      "以上内容依据《小学初中义务教育数学》课标截图整理：前三张图用于整体简述，表 1 的各项素养内涵按原文完整保留。",
  },
  "math:junior": {
    headline: "义务教育数学（初中）",
    summary:
      "义务教育数学课程以核心素养为导向，强调学生在数学学习中逐步形成面向未来发展所需的关键能力。整体上可概括为：会用数学的眼光观察现实世界，会用数学的思维思考现实世界，会用数学的语言表达现实世界。初中阶段侧重对概念的理解。",
    sections: [
      {
        title: "核心素养整体说明",
        blocks: [
          {
            title: "会用数学的眼光观察现实世界",
            body:
              "通过数学的眼光，可以从现实世界的客观现象中发现数量关系与空间形式，提出有意义的数学问题；能够抽象出数学的研究对象及其属性，形成概念、关系与结构；能够理解自然现象背后的数学原理，感悟数学的审美价值，形成对数学的好奇心与想象力，主动参与数学探究活动，发展创新意识。",
            source: "课标第 12 页",
          },
          {
            title: "会用数学的思维思考现实世界",
            body:
              "通过数学的思维，可以揭示客观事物的本质属性，建立数学对象之间、数学与现实世界之间的逻辑联系；能够根据已知事实或原理，合乎逻辑地推出结论，构建数学的逻辑体系；能够运用符号运算、形式推理等数学方法，分析、解决数学问题和实际问题。",
            source: "课标第 13 页",
          },
          {
            title: "会用数学的语言表达现实世界",
            body:
              "通过数学的语言，可以简约、精确地描述自然现象、科学情境和日常生活中的数量关系与空间形式；能够在现实生活与其他学科中构建普适的数学模型，表达和解决问题；能够理解数据的意义与价值，会用数据的分析结果解释和预测不确定现象，形成合理的判断或决策。",
            source: "课标第 13-14 页",
          },
          {
            title: "初中阶段主要表现",
            body:
              "初中阶段，核心素养主要表现为：抽象能力、运算能力、几何直观、空间观念、推理能力、数据观念、模型观念、应用意识、创新意识。",
            source: "课标第 14 页",
          },
        ],
      },
      {
        title: "核心素养主要表现及其内涵",
        blocks: [
          {
            title: "抽象能力",
            body:
              "抽象能力主要是指通过对现实世界中数量关系与空间形式的抽象，得到数学的研究对象，形成数学概念、性质、法则和方法的能力。能够从实际情境或跨学科的问题中抽象出核心变量、变量的规律及变量之间的关系，并能够用数学符号予以表达；能够从具体的问题解决中概括出一般结论，形成数学的方法与策略。感悟数学抽象对于数学产生与发展的作用，感悟数学的眼光观察现实世界的意义，形成数学想象力，提高学习数学的兴趣。",
            source: "表 1，初中",
          },
          {
            title: "运算能力",
            body:
              "运算能力主要是指根据法则和运算律进行正确运算的能力。能够明晰运算的对象和意义，理解算法与算理之间的关系；能够理解运算的问题，选择合理简洁的运算策略解决问题；能够通过运算促进数学推理能力的发展。运算能力有助于形成规范化思考问题的品质，养成一丝不苟、严谨求实的科学态度。",
            source: "表 1，小学与初中",
          },
          {
            title: "几何直观",
            body:
              "几何直观主要是指运用图表描述和分析问题的意识与习惯。能够感知各种几何图形及其组成元素，依据图形的特征进行分类；根据语言描述画出相应的图形，分析图形的性质，建立形与数的联系，构建数学问题的直观模型；利用图表分析实际情境与数学问题，探索解决问题的思路。几何直观有助于把握问题的本质，明晰思维的路径。",
            source: "表 1，小学与初中",
          },
          {
            title: "空间观念",
            body:
              "空间观念主要是指对空间物体或图形的形状、大小及位置关系的认识。能够根据物体特征抽象出几何图形，根据几何图形想象其所描述的实际物体；想象并表达物体的空间方位和相互之间的位置关系；感知并描述图形的运动和变化规律。空间观念有助于理解现实生活中空间物体的形态与结构，是形成空间想象力的经验基础。",
            source: "表 1，小学与初中",
          },
          {
            title: "推理能力",
            body:
              "推理能力主要是指从一些事实和命题出发，依据规则推出其他命题或结论的能力。理解逻辑推理在形成数学概念、法则、定理和解决问题中的重要性，初步掌握推理的基本形式和规则；对于一些简单问题，能通过特殊结果推断一般结论；理解命题的结构与联系，探索并表达论证过程；感悟数学的严谨性，初步形成逻辑表达与交流的习惯。推理能力有助于逐步养成重论据、合乎逻辑的思维习惯，形成实事求是的科学态度与理性精神。",
            source: "表 1，初中",
          },
          {
            title: "数据观念",
            body:
              "数据观念主要是指对数据的意义和随机性有比较清晰的认识。知道数据蕴含着信息，需要根据问题的背景和所要研究的问题确定数据收集、整理和分析的方法；知道可以用定量的方法描述随机现象的变化趋势及随机事件发生的可能性大小。形成数据观念有助于理解和表达生活中随机现象发生的机理，感知大数据时代数据分析的重要性，养成重证据、讲道理的科学态度。",
            source: "表 1，初中",
          },
          {
            title: "模型观念",
            body:
              "模型观念主要是指对运用数学模型解决实际问题有清晰的认识。知道数学建模是数学与现实联系的基本途径；初步感知数学建模的基本过程，从现实生活或具体情境中抽象出数学问题，用数学符号建立方程、不等式、函数等表示数学问题中的数量关系和变化规律，求出结果并对该结果的意义作出解释。模型观念有助于开展跨学科主题学习，感悟数学应用的普遍性。",
            source: "表 1，初中",
          },
          {
            title: "应用意识",
            body:
              "应用意识主要是指有意识地利用数学的概念、原理和方法解释现实世界中的现象与规律，解决现实世界中的问题。能够感知生活中蕴含着大量的与数量和图形有关的问题，可以用数学的方法予以解决；初步了解数学作为一种通用的科学语言在其他学科中的应用，通过跨学科主题学习建立不同学科之间的联系。应用意识有助于用学过的知识和方法解决简单的实际问题，养成理论联系实际的习惯，发展实践能力。",
            source: "表 1，小学与初中",
          },
          {
            title: "创新意识",
            body:
              "创新意识主要是指主动尝试从日常生活、自然现象或科学情境中发现和提出有意义的数学问题。初步学会通过具体的实例，运用归纳和类比发现数学关系与规律，提出数学命题与猜想，并加以验证；勇于探索一些开放性的、非常规的实际问题与数学问题。创新意识有助于形成独立思考、敢于质疑的科学态度与理性精神。",
            source: "表 1，小学与初中",
          },
        ],
      },
      {
        title: "核心素养水平",
        blocks: SHARED_COMPETENCY_LEVEL_BLOCKS,
      },
    ],
    sourceNote:
      "以上内容依据《小学初中义务教育数学》课标截图整理：前三张图用于整体简述，表 1 的各项素养内涵按原文完整保留。",
  },
  "math:senior": {
    headline: "普通高中数学",
    summary:
      "普通高中数学课程标准将数学学科核心素养界定为数学课程目标的集中体现，包括数学抽象、逻辑推理、数学建模、直观想象、数学运算和数据分析。结合附录中的水平划分，这些核心素养都可以按“水平一、水平二、水平三”理解为由熟悉情境到关联情境，再到综合情境的递进发展。",
    sections: [
      {
        title: "数学学科核心素养",
        blocks: [
          {
            title: "数学抽象",
            body:
              "数学抽象是指通过对数量关系与空间形式的抽象，得到数学研究对象的素养。主要包括：从数量与数量关系、图形与图形关系中抽象出数学概念及概念之间的关系，从事物的具体背景中抽象出一般规律和结构，并用数学语言予以表征。数学抽象是数学的基本思想，是形成理性思维的重要基础，反映了数学的本质特征。",
            source: "课标第 12 页、截图第 1-2 张",
          },
          {
            title: "逻辑推理",
            body:
              "逻辑推理是指从一些事实和命题出发，依据规则推出其他命题的素养。主要包括两类：一类是从特殊到一般的推理，推理形式主要有归纳、类比；一类是从一般到特殊的推理，推理形式主要有演绎。逻辑推理是得到数学结论、构建数学体系的重要方式，是数学严谨性的基本保证。",
            source: "课标第 13 页、截图第 2 张",
          },
          {
            title: "数学建模",
            body:
              "数学建模是对现实问题进行数学抽象，用数学语言表达问题、用数学方法构建模型解决问题的素养。数学建模过程主要包括：在实际情境中从数学的视角发现问题、提出问题、分析问题、建立模型、确定参数、计算求解、检验结果、改进模型，最终解决实际问题。数学建模搭建了数学与外部世界联系的桥梁，是数学应用的重要形式。",
            source: "课标第 13-14 页、截图第 2-3 张",
          },
          {
            title: "直观想象",
            body:
              "直观想象是指借助几何直观和空间想象感知事物的形态与变化，利用空间形式特别是图形，理解和解决数学问题的素养。主要包括：借助空间形式认识事物的位置关系、形态变化与运动规律；利用图形描述、分析数学问题，建立形与数的联系，构建数学问题的直观模型，探索解决问题的思路。直观想象是发现和提出问题、分析和解决问题的重要手段。",
            source: "课标第 14 页、截图第 3 张",
          },
          {
            title: "数学运算",
            body:
              "数学运算是指在明晰运算对象的基础上，依据运算法则解决数学问题的素养。主要包括：理解运算对象，掌握运算法则，探究运算思路，选择运算方法，设计运算程序，求得运算结果等。数学运算是解决数学问题的基本手段，也是演绎推理和计算机解决问题的重要基础。",
            source: "课标第 15 页、截图第 4 张",
          },
          {
            title: "数据分析",
            body:
              "数据分析是指针对研究对象获取数据，运用数学方法对数据进行整理、分析和推断，形成关于研究对象知识的素养。数据分析过程主要包括：收集数据、整理数据、提取信息、构建模型、进行推断、获得结论。数据分析是研究随机现象的重要数学技术，是大数据时代数学应用的主要方法之一。",
            source: "课标第 15 页、截图第 4 张",
          },
        ],
      },
      {
        title: "核心素养水平",
        blocks: SHARED_COMPETENCY_LEVEL_BLOCKS,
      },
    ],
    sourceNote:
      "以上内容依据《普通高中数学课程标准（2017年版 2020年修订）》正文与附录 1 整理：六项核心素养按原文扩写，水平一/二/三整合为通用于各核心素养的层级说明。",
  },
};

function PositioningView() {
  return (
    <>
      <Row id="overview-metrics" gutter={[16, 16]} className="page-section-anchor overview-positioning-grid">
        {positioningCards.map((item) => (
          <Col key={item.title} xs={24} md={12}>
            <Card className="overview-summary-card">
              <Space direction="vertical" size={10} style={{ width: "100%" }}>
                <Space align="center" size={10}>
                  <span className="overview-summary-card__icon">{item.icon}</span>
                  <Typography.Text type="secondary">{item.title}</Typography.Text>
                </Space>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {item.value}
                </Typography.Title>
                <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
                  {item.description}
                </Typography.Paragraph>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} className="overview-positioning-board-row">
        <Col id="overview-definitions" xs={24} lg={12} className="page-section-anchor">
          <Card title="当前标注维度" className="overview-board-card">
            <div className="overview-dimension-grid">
              {annotationDimensions.map((item) => (
                <div key={item.title} className="overview-dimension-card">
                  <Space direction="vertical" size={8} style={{ width: "100%" }}>
                    <Space align="center" size={8}>
                      <Typography.Text strong>{item.title}</Typography.Text>
                      <Tag color={item.status === "当前重点" ? "cyan" : "blue"}>{item.status}</Tag>
                    </Space>
                    <Typography.Text type="secondary">{item.description}</Typography.Text>
                  </Space>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col id="overview-references" xs={24} lg={12} className="page-section-anchor">
          <Card title="判定逻辑" className="overview-board-card">
            <div className="overview-step-list">
              {workflowSteps.map((item, index) => (
                <div key={item} className="overview-step-item">
                  <div className="overview-step-item__index">{index + 1}</div>
                  <Typography.Text>{item}</Typography.Text>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </>
  );
}

function EmptyDefinitionState({ subject, stage }: { subject: SubjectKey; stage: StageKey }) {
  const subjectLabel = subject === "math" ? "数学" : "物理";
  const stageLabel = stageOptions.find((item) => item.value === stage)?.label ?? stage;

  return (
    <Card className="overview-board-card">
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={`${subjectLabel} / ${stageLabel} 暂无可严格引用的标准定义`}
      />
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        当前首页只展示能够从你提供的标准文件中直接确认的定义内容。这个筛选组合暂时不补写推断性文案。
      </Typography.Paragraph>
    </Card>
  );
}

function DefinitionsView({
  subject,
  stage,
}: {
  subject: SubjectKey;
  stage: StageKey;
}) {
  const dataset = datasetMap[`${subject}:${stage}`];

  if (!dataset) {
    return <EmptyDefinitionState subject={subject} stage={stage} />;
  }

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card id="overview-definitions" className="overview-board-card page-section-anchor">
        <Space direction="vertical" size={10} style={{ width: "100%" }}>
          <div>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {dataset.headline}
            </Typography.Title>
            <Typography.Paragraph className="overview-definition-summary" style={{ margin: "10px 0 0" }}>
              {dataset.summary}
            </Typography.Paragraph>
          </div>
          <Tag icon={<BookOutlined />} className="overview-source-note">
            {dataset.sourceNote}
          </Tag>
        </Space>
      </Card>

      {dataset.sections.map((section) => (
        <Card key={section.title} title={section.title} className="overview-board-card">
          <div className="overview-definition-grid overview-definition-grid--single">
            {section.blocks.map((block) => (
              <div key={block.title} className="overview-definition-card">
                <Space direction="vertical" size={8} style={{ width: "100%" }}>
                  <Typography.Text strong>{block.title}</Typography.Text>
                  <Typography.Paragraph className="overview-definition-body" style={{ margin: 0 }}>
                    {block.body}
                  </Typography.Paragraph>
                </Space>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </Space>
  );
}

export function HomePage() {
  usePageHashScroll();

  const [mode, setMode] = useState<OverviewMode>("positioning");
  const [subject, setSubject] = useState<SubjectKey>("math");
  const [stage, setStage] = useState<StageKey>("senior");

  const heroTags = useMemo(() => {
    if (mode === "positioning") {
      return ["题目级标注治理", "核心素养矩阵", "标准口径统一"];
    }
    const subjectLabel = subject === "math" ? "数学" : "物理";
    const stageLabel = stageOptions.find((item) => item.value === stage)?.label ?? stage;
    return [subjectLabel, stageLabel, "按标准原文展示"];
  }, [mode, stage, subject]);

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }} className="overview-page">
      <Card id="overview-hero" className="hero-panel page-section-anchor overview-hero">
        <div className="overview-hero__content">
          <div className="overview-hero__copy">
            <Typography.Title level={2} style={{ marginTop: 0, marginBottom: 10 }}>
              项目总览
            </Typography.Title>
            <Typography.Paragraph className="overview-hero__paragraph">
              首页现在聚焦两件事：说明系统当前做什么，以及在有标准依据的前提下，展示不同学科、学段的打标定义。
            </Typography.Paragraph>
            <Space wrap>
              {heroTags.map((item) => (
                <Tag key={item} color="cyan">
                  {item}
                </Tag>
              ))}
            </Space>
          </div>

          <div className="overview-hero__controls">
            <div className="overview-hero__control-card">
              <Typography.Text strong>内容切换</Typography.Text>
              <Segmented
                block
                value={mode}
                options={modeOptions}
                onChange={(value: string | number) => setMode(value as OverviewMode)}
              />
              <Typography.Text type="secondary">
                “打标定义”页只保留能从标准文件直接确认的内容。
              </Typography.Text>
            </div>
          </div>
        </div>
      </Card>

      {mode === "positioning" ? (
        <PositioningView />
      ) : (
        <>
          <Card id="overview-metrics" className="overview-board-card page-section-anchor">
            <div className="overview-filter-bar">
              <div className="overview-filter-bar__header">
                <Space align="center" size={8}>
                  <FilterOutlined />
                  <Typography.Text strong>筛选条件</Typography.Text>
                </Space>
                <Typography.Text type="secondary">
                  按学科与学段关键词筛选展示内容；同一学段下按统一素养体系展示。
                </Typography.Text>
              </div>

              <div className="overview-filter-bar__controls">
                <div className="overview-filter-group">
                  <Typography.Text type="secondary">学科</Typography.Text>
                  <Segmented
                    block
                    value={subject}
                    options={subjectOptions}
                    onChange={(value: string | number) => setSubject(value as SubjectKey)}
                  />
                </div>

                <div className="overview-filter-group">
                  <Typography.Text type="secondary">学段</Typography.Text>
                  <Segmented
                    block
                    value={stage}
                    options={stageOptions}
                    onChange={(value: string | number) => setStage(value as StageKey)}
                  />
                </div>
              </div>
            </div>
          </Card>

          <DefinitionsView subject={subject} stage={stage} />

          <Card id="overview-references" title="标准依据" className="overview-board-card page-section-anchor">
            <div className="overview-source-list">
              {strictSourceNotes.map((item) => (
                <div key={item.title} className="overview-source-card">
                  <Space direction="vertical" size={6} style={{ width: "100%" }}>
                    <Space align="center" size={8}>
                      <ReadOutlined />
                      <Typography.Text strong>{item.title}</Typography.Text>
                    </Space>
                    <Typography.Text type="secondary">{item.detail}</Typography.Text>
                    <Tag icon={<BookOutlined />}>{item.fileName}</Tag>
                  </Space>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </Space>
  );
}
