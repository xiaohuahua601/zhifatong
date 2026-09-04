/**
 * 智法通 - 合同审查页面（结构化科技组件重构版）
 *
 * 包含合同上传（拖拽上传）、合同列表、审查报告展示、
 * 风险条款高亮、风险评分读出、修改建议卡片和审查流程节点带。
 *
 * 视觉形态：tech-frame 科技框架 / diamond 菱形流程节点 / hex 六边形徽章 /
 * readout 终端读出 / corner-brackets 角括号 / tech-section-header 区块头 /
 * page-grid-bg 页面网格背景 / tech-scan 扫描线。
 */

<template>
  <div class="contract-page fade-in">
    <!-- 页面级网格纹理背景层 -->
    <div class="page-grid-bg"></div>

    <!-- ==================== 顶部操作区 · 结构化区块头形态 ==================== -->
    <div class="page-header">
      <div class="tech-section-header page-title-header">
        <span class="hex-badge page-title-hex"><el-icon :size="15"><Files /></el-icon></span>
        <h2 class="tsh-title gradient-title">合同审查</h2>
        <span class="tsh-sub">CONTRACT REVIEW</span>
        <span class="tsh-line"></span>
        <div class="tsh-extra header-actions">
          <!-- 额度提示：管理员无份数限制，普通用户显示剩余份数 -->
          <span class="quota-hint">
            <el-icon :size="13"><Coin /></el-icon>
            <strong v-if="userStore.isAdmin">管理员无份数限制</strong>
            <template v-else>
              今日剩余合同审查份数：<strong>{{ remainingQuota }}</strong> 份
            </template>
          </span>
          <!-- 上传按钮 - shimmer微光效果 -->
          <el-button type="primary" class="shimmer-btn" @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            上传合同
            <div class="shimmer-overlay"></div>
          </el-button>
        </div>
      </div>
    </div>

    <!-- ==================== 统计概览条 · tech-frame + 终端读出阵列 ==================== -->
    <div class="stats-bar tech-frame">
      <div class="stat-item clickable" :class="{ active: activeStatFilter === null }" @click="activeStatFilter = null">
        <span class="readout-box"><span class="data-readout stat-value">{{ contracts.length }}</span></span>
        <span class="stat-meta">
          <span class="status-light light-cyan"></span>
          <span class="stat-label tech-label">合同总数</span>
        </span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item clickable" :class="{ active: activeStatFilter === 'reviewed' }" @click="handleStatClick('reviewed')">
        <span class="readout-box"><span class="data-readout stat-value stat-success">{{ reviewedCount }}</span></span>
        <span class="stat-meta">
          <span class="status-light is-on"></span>
          <span class="stat-label tech-label">已审查</span>
        </span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item clickable" :class="{ active: activeStatFilter === 'pending' }" @click="handleStatClick('pending')">
        <span class="readout-box"><span class="data-readout stat-value stat-warning">{{ pendingCount }}</span></span>
        <span class="stat-meta">
          <span class="status-light is-warn"></span>
          <span class="stat-label tech-label">待审查</span>
        </span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item clickable" @click="handleStatClick('score')">
        <span class="readout-box"><span class="data-readout stat-value stat-accent">{{ avgScore }}</span></span>
        <span class="stat-meta">
          <span class="status-light light-gold"></span>
          <span class="stat-label tech-label">平均评分</span>
        </span>
      </div>
    </div>

    <!-- 筛选状态提示条 -->
    <div v-if="activeStatFilter" class="filter-hint-bar">
      <span>
        <el-icon><Filter /></el-icon>
        当前筛选：{{ activeStatFilter === 'reviewed' ? '已审查合同' : '待审查合同' }}（共 {{ filteredContracts.length }} 份）
      </span>
      <el-button type="info" size="small" link @click="activeStatFilter = null">清除筛选</el-button>
    </div>

    <!-- ==================== 合同列表 · tech-frame 框架形态 ==================== -->
    <div class="contract-list tech-frame">
      <div class="tech-section-header list-sh">
        <span class="tsh-bar"></span>
        <span class="tsh-title">合同档案库</span>
        <span class="tsh-sub">CONTRACT ARCHIVE</span>
        <span class="tsh-line"></span>
        <span class="tsh-extra">
          <span class="status-light is-on"></span>
          实时同步
        </span>
      </div>
      <el-table
        :data="filteredContracts"
        style="width: 100%"
        :header-cell-style="{ background: 'rgba(23, 29, 42, 0.85)', color: '#a8a294', borderBottom: '1px solid rgba(90, 118, 165, 0.22)' }"
        :cell-style="{ background: 'transparent', color: '#ece7da', borderBottom: '1px solid rgba(90, 118, 165, 0.12)' }"
        @row-click="handleRowClick"
        :row-class-name="tableRowClassName"
      >
        <el-table-column prop="title" label="合同名称" min-width="200" />
        <el-table-column prop="contract_type" label="合同类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.contract_type || '未分类' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="overall_score" label="风险评分" width="140">
          <template #default="{ row }">
            <div v-if="row.overall_score !== null && row.overall_score !== undefined" class="score-cell score-animate">
              <el-progress
                type="dashboard"
                :percentage="Math.round(row.overall_score)"
                :width="40"
                :stroke-width="4"
                :color="getScoreColor(row.overall_score)"
              />
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag
              v-if="row.risk_level"
              :type="getRiskLevelType(row.risk_level)"
              size="small"
              effect="dark"
              class="risk-tag-glow"
            >
              {{ row.risk_level }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="350" fixed="right">
          <template #default="{ row }">
            <!-- 开始审查：uploaded(待解析)/parsed(已解析)/failed(失败) 状态可启动AI审查 -->
            <el-button
              v-if="['uploaded', 'parsed', 'failed'].includes(row.status)"
              type="primary"
              size="small"
              class="action-btn"
              @click.stop="handleReview(row.id)"
            >
              开始审查
            </el-button>
            <!-- 查看报告：reviewed(已审查) 状态可查看完整AI审查报告 -->
            <el-button
              v-if="row.status === 'reviewed'"
              type="success"
              size="small"
              class="action-btn"
              @click.stop="handleViewReport(row.id)"
            >
              查看报告
            </el-button>
            <!-- 优化并下载：reviewed状态可基于审查报告修改建议生成优化版合同并下载（V6.0.6新增） -->
            <el-button
              v-if="row.status === 'reviewed'"
              type="warning"
              size="small"
              plain
              class="action-btn"
              :loading="optimizingIds.has(row.id)"
              @click.stop="handleOptimizeDownload(row)"
            >
              {{ optimizingIds.has(row.id) ? '优化中...' : '优化并下载' }}
            </el-button>
            <!-- 处理中：parsing(解析中)/reviewing(审查中) 状态显示禁用按钮 -->
            <el-button
              v-if="['parsing', 'reviewing'].includes(row.status)"
              type="warning"
              size="small"
              class="action-btn"
              disabled
              :loading="true"
            >
              处理中
            </el-button>
            <!-- 编辑分类：支持「未分类」合同归档管理 -->
            <el-button
              type="info"
              size="small"
              plain
              class="action-btn"
              @click.stop="handleEditCategory(row)"
            >
              编辑分类
            </el-button>
            <el-button
              type="danger"
              size="small"
              plain
              class="action-btn"
              @click.stop="handleDelete(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadContracts"
        />
      </div>
    </div>

    <!-- ==================== 上传对话框 · tech-frame + 常驻扫描线 ==================== -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传合同"
      width="560px"
      :close-on-click-modal="false"
      class="upload-dialog"
    >
      <div
        class="upload-area tech-frame"
        :class="{ dragging: isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInputRef"
          type="file"
          accept=".pdf,.doc,.docx,.txt"
          style="display: none"
          @change="handleFileSelect"
        />
        <!-- 常驻扫描内容层 -->
        <div class="upload-inner tech-scan scan-always">
          <!-- 大图标 hex 形态 -->
          <span class="hex-badge upload-hex"><el-icon :size="26"><Upload /></el-icon></span>
          <p class="upload-text">拖拽合同文件到此处，或点击选择上传</p>
          <!-- 支持格式 chips -->
          <div class="upload-chips">
            <span class="format-chip">PDF</span>
            <span class="format-chip">Word / DOC / DOCX</span>
            <span class="format-chip">TXT</span>
            <span class="format-chip">最大 50MB</span>
          </div>
          <!-- 拖拽提示 -->
          <p class="upload-hint">
            <span class="status-light is-on"></span>
            拖拽上传 · 点击选择 · 上传后自动解析合同文本
          </p>
        </div>
      </div>
      <!-- 文件选择后 - 成功勾选动画 -->
      <transition name="file-selected">
        <div v-if="selectedFile" class="selected-file file-selected-animate">
          <div class="file-check-icon">
            <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="10" cy="10" r="9" stroke="#7ca586" stroke-width="1.5" fill="rgba(124, 165, 134, 0.1)"/>
              <path d="M6 10L9 13L14 7" stroke="#7ca586" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <el-icon :size="20"><Document /></el-icon>
          <span>{{ selectedFile.name }}</span>
          <el-icon class="remove-file" @click="selectedFile = null"><Close /></el-icon>
        </div>
      </transition>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!selectedFile"
          @click="handleUpload"
          class="upload-submit-btn"
        >
          {{ uploading ? '上传中...' : '上传并解析' }}
          <!-- 上传进度渐变条 -->
          <div v-if="uploading" class="upload-progress-bar"></div>
        </el-button>
      </template>
    </el-dialog>

    <!-- ==================== 审查报告对话框 · 结构化区块重构 ==================== -->
    <el-dialog
      v-model="showReportDialog"
      title="合同审查报告"
      width="800px"
      class="report-dialog"
      destroy-on-close
    >
      <div v-if="report" class="report-content">
        <!-- 总体评分 · readout 终端读出形态 -->
        <div class="report-overview report-stagger" style="--stagger-delay: 0s">
          <div class="overview-score">
            <span class="tech-label">OVERALL RISK SCORE</span>
            <div class="readout-box score-readout">
              <span class="data-readout score-number">{{ animatedScore }}</span>
              <span class="score-unit">/100</span>
            </div>
            <span class="tech-label">综合风险评分</span>
          </div>
          <div class="overview-divider"></div>
          <div class="overview-details">
            <div class="detail-item">
              <span class="detail-label">风险等级</span>
              <el-tag :type="getRiskLevelType(report.risk_level || '')" effect="dark" size="large" class="risk-tag-glow">
                {{ report.risk_level || '未知' }}
              </el-tag>
            </div>
            <div class="detail-item">
              <span class="detail-label">风险条款数</span>
              <span class="detail-value data-readout">{{ report.risk_clause_count }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">审查耗时</span>
              <span class="detail-value">{{ report.review_duration_ms ? (report.review_duration_ms / 1000).toFixed(1) + 's' : '-' }}</span>
            </div>
          </div>
        </div>

        <!-- 审查维度评分 - 藏青质感轨道 -->
        <div class="dimension-scores report-stagger" style="--stagger-delay: 0.1s">
          <div class="tech-section-header dim-sh">
            <span class="tsh-bar"></span>
            <span class="tsh-title">审查维度</span>
            <span class="tsh-sub">DIMENSIONS</span>
            <span class="tsh-line"></span>
          </div>
          <div class="dimension-item">
            <span class="dim-label">完整性</span>
            <div class="dim-track">
              <div
                class="dim-fill dim-fill-gold"
                :style="{ width: parseDimScore(report.completeness) + '%' }"
              ></div>
            </div>
            <span class="dim-value">{{ parseDimScore(report.completeness) }}%</span>
          </div>
          <div class="dimension-item">
            <span class="dim-label">合规性</span>
            <div class="dim-track">
              <div
                class="dim-fill dim-fill-green"
                :style="{ width: parseDimScore(report.compliance) + '%' }"
              ></div>
            </div>
            <span class="dim-value">{{ parseDimScore(report.compliance) }}%</span>
          </div>
          <div class="dimension-item">
            <span class="dim-label">一致性</span>
            <div class="dim-track">
              <div
                class="dim-fill dim-fill-blue"
                :style="{ width: parseDimScore(report.consistency) + '%' }"
              ></div>
            </div>
            <span class="dim-value">{{ parseDimScore(report.consistency) }}%</span>
          </div>
        </div>

        <!-- 审查摘要 -->
        <div v-if="report.summary" class="report-section report-stagger" style="--stagger-delay: 0.2s">
          <div class="tech-section-header report-sh">
            <span class="tsh-bar"></span>
            <span class="tsh-title">审查摘要</span>
            <span class="tsh-sub">SUMMARY</span>
            <span class="tsh-line"></span>
          </div>
          <p class="summary-text">{{ report.summary }}</p>
        </div>

        <!-- 风险条款 - 菱形节点 + 角括号原文块 -->
        <div v-if="report.risk_clauses && report.risk_clauses.length > 0" class="report-section report-stagger" style="--stagger-delay: 0.3s">
          <div class="tech-section-header report-sh">
            <span class="tsh-bar"></span>
            <span class="tsh-title">风险条款</span>
            <span class="tsh-sub">RISK CLAUSES</span>
            <span class="tsh-line"></span>
            <span class="tsh-extra">
              <span class="data-readout">{{ report.risk_clauses.length }}</span>
              <span>条已识别</span>
            </span>
          </div>
          <div
            v-for="(clause, idx) in report.risk_clauses"
            :key="idx"
            class="risk-clause-card"
            :class="'risk-level-' + getRiskLevelClass(clause.risk_level || clause.level || '中')"
          >
            <div class="risk-header" @click="toggleClause(idx)">
              <span class="diamond-node clause-node"></span>
              <el-tag :type="getRiskLevelType(clause.risk_level || clause.level || '中')" size="small" effect="dark">
                {{ clause.risk_level || clause.level || '中' }}风险
              </el-tag>
              <span class="clause-title">{{ clause.clause_title || clause.title || `条款 ${idx + 1}` }}</span>
              <!-- 展开/折叠箭头 -->
              <span class="clause-collapse-arrow" :class="{ expanded: isClauseExpanded(idx) }"></span>
            </div>
            <!-- 展开/折叠动画 -->
            <transition name="clause-expand">
              <div v-show="isClauseExpanded(idx)" class="clause-body">
                <div class="clause-content corner-brackets">{{ clause.clause_content || clause.content }}</div>
                <div v-if="clause.suggestion || clause.modification" class="clause-suggestion">
                  <div class="suggestion-icon">
                    <el-icon :size="14" color="#c9a962"><EditPen /></el-icon>
                  </div>
                  <span>修改建议：{{ clause.suggestion || clause.modification }}</span>
                </div>
              </div>
            </transition>
          </div>
        </div>

        <!-- ==================== V4.0 多Agent对抗式审查结果（角色面板阵列）==================== -->
        <div v-if="hasAdversarialReview" class="adversarial-section report-stagger" style="--stagger-delay: 0.35s">
          <div class="tech-section-header adversarial-sh">
            <span class="hex-badge adversarial-hex">V4</span>
            <span class="tsh-title">多Agent对抗式审查</span>
            <span class="tsh-sub">ADVERSARIAL REVIEW</span>
            <el-tooltip content="主审Agent(中立) + 复核Agent(规则) + 反方Agent(弱势方) 三方博弈，降低风险漏报率" placement="top">
              <el-icon class="title-info-icon"><InfoFilled /></el-icon>
            </el-tooltip>
            <span class="tsh-line"></span>
          </div>

          <!-- 三方博弈角色面板阵列 -->
          <div class="role-grid">
            <div class="role-panel role-primary">
              <div class="role-head">
                <span class="hex-badge role-hex"><el-icon :size="13"><Aim /></el-icon></span>
                <span class="role-name">主审Agent</span>
              </div>
              <div class="readout-box role-readout">
                <span class="data-readout role-value">{{ primaryRisksCount }}</span>
              </div>
              <span class="role-desc">识别风险 · 条</span>
            </div>
            <div class="role-panel role-review">
              <div class="role-head">
                <span class="hex-badge hex-cyan role-hex"><el-icon :size="13"><Checked /></el-icon></span>
                <span class="role-name">复核Agent</span>
              </div>
              <div class="readout-box role-readout">
                <span class="data-readout role-value">{{ reviewApprovedCount }}</span>
              </div>
              <span class="role-desc">规则确认 / {{ primaryRisksCount }}条</span>
            </div>
            <div class="role-panel role-adverse">
              <div class="role-head">
                <span class="hex-badge hex-pink role-hex"><el-icon :size="13"><Switch /></el-icon></span>
                <span class="role-name">反方Agent</span>
              </div>
              <div class="readout-box role-readout">
                <span class="data-readout role-value">{{ report.adverse_opinion_count || 0 }}</span>
              </div>
              <span class="role-desc">弱势方质疑 · 条</span>
            </div>
            <div class="role-panel role-debate">
              <div class="role-head">
                <span class="hex-badge hex-gold role-hex"><el-icon :size="13"><ChatDotRound /></el-icon></span>
                <span class="role-name">对抗辩论</span>
              </div>
              <div class="readout-box role-readout">
                <span class="data-readout role-value">{{ debateRoundsCount }}</span>
              </div>
              <span class="role-desc">多轮博弈 · 轮</span>
            </div>
            <div class="role-panel role-unresolved">
              <div class="role-head">
                <span class="hex-badge hex-danger role-hex"><el-icon :size="13"><WarningFilled /></el-icon></span>
                <span class="role-name">未解决争议</span>
              </div>
              <div class="readout-box role-readout">
                <span class="data-readout role-value">{{ report.unresolved_count || 0 }}</span>
              </div>
              <span class="role-desc">建议人工复核</span>
            </div>
          </div>

          <!-- 复核Agent规则复检结果 -->
          <div v-if="reviewCheckData && reviewCheckData.approved_count !== undefined" class="adversarial-subsection">
            <div class="tech-section-header sub-sh">
              <span class="hex-badge hex-cyan sub-hex">复</span>
              <span class="tsh-title">复核Agent · 规则引擎复检</span>
              <span class="tsh-line"></span>
            </div>
            <div class="review-check-grid">
              <div class="review-check-item approved">
                <span class="check-label">
                  <span class="status-light is-on"></span>
                  规则确认
                </span>
                <span class="check-count data-readout">{{ reviewCheckData.approved_count || 0 }}</span>
              </div>
              <div class="review-check-item disputed">
                <span class="check-label">
                  <span class="status-light is-warn"></span>
                  待争议
                </span>
                <span class="check-count data-readout">{{ reviewCheckData.disputed_count || 0 }}</span>
              </div>
              <div class="review-check-item missed">
                <span class="check-label">
                  <span class="status-light light-danger"></span>
                  主审遗漏
                </span>
                <span class="check-count data-readout">{{ reviewCheckData.missed_count || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- 反方Agent反对意见 -->
          <div v-if="adverseOpinionsData.length > 0" class="adversarial-subsection">
            <div class="tech-section-header sub-sh">
              <span class="hex-badge hex-pink sub-hex">反</span>
              <span class="tsh-title">反方Agent · 弱势方立场质疑</span>
              <span class="tsh-line"></span>
            </div>
            <div class="adverse-opinions-list">
              <div
                v-for="(opinion, idx) in adverseOpinionsData"
                :key="'ao-' + idx"
                class="adverse-opinion-card corner-brackets"
              >
                <div class="opinion-header">
                  <span class="diamond-node node-pink"></span>
                  <el-tag type="danger" size="small" effect="plain">条款 {{ opinion.clause_index }}</el-tag>
                  <span class="opposition-text">{{ opinion.opposition }}</span>
                </div>
                <div v-if="opinion.weak_party_impact" class="opinion-detail">
                  <span class="detail-label">弱势方影响：</span>{{ opinion.weak_party_impact }}
                </div>
                <div v-if="opinion.demanded_revision" class="opinion-detail demand">
                  <span class="detail-label">要求修改：</span>{{ opinion.demanded_revision }}
                </div>
              </div>
            </div>
          </div>

          <!-- 对抗辩论记录时间轴 -->
          <div v-if="debateLogData.length > 0" class="adversarial-subsection">
            <div class="tech-section-header sub-sh">
              <span class="hex-badge hex-gold sub-hex">辩</span>
              <span class="tsh-title">对抗辩论记录 · 可审计可回溯</span>
              <span class="tsh-line"></span>
            </div>
            <div class="debate-timeline">
              <div
                v-for="(debate, idx) in debateLogData"
                :key="'debate-' + idx"
                class="debate-round"
              >
                <div class="round-marker">
                  <span class="hex-badge hex-gold round-hex">{{ debate.round }}</span>
                </div>
                <div class="round-content">
                  <div class="round-status">
                    <el-tag
                      :type="debate.status === 'consensus' ? 'success' : (debate.status === 'unresolved' ? 'danger' : 'warning')"
                      size="small"
                      effect="dark"
                    >
                      {{ debate.status === 'consensus' ? '达成共识' : (debate.status === 'unresolved' ? '未解决' : debate.status) }}
                    </el-tag>
                  </div>
                  <div v-if="debate.issue" class="round-issue">争议点：{{ debate.issue }}</div>
                  <div class="round-response primary-response">
                    <span class="diamond-node node-cyan resp-node"></span>
                    <span class="response-text"><span class="response-label">主审：</span>{{ debate.primary_response }}</span>
                  </div>
                  <div class="round-response adverse-response">
                    <span class="diamond-node node-pink resp-node"></span>
                    <span class="response-text"><span class="response-label">反方：</span>{{ debate.adverse_response }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 未解决问题警示（红系） -->
          <div v-if="unresolvedIssuesData.length > 0" class="unresolved-warning">
            <span class="diamond-node node-danger"></span>
            <span>共 {{ unresolvedIssuesData.length }} 条争议未达成共识，建议人工复核以下条款：</span>
            <div class="unresolved-list">
              <el-tag
                v-for="(issue, idx) in unresolvedIssuesData"
                :key="'unresolved-' + idx"
                type="danger"
                size="small"
                effect="plain"
                class="unresolved-tag"
              >
                条款 {{ issue.clause_index }}：{{ issue.issue }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 修改建议 - 六边形编号 + 角括号原文引用 -->
        <div class="report-section report-stagger" style="--stagger-delay: 0.4s">
          <div class="tech-section-header report-sh">
            <span class="tsh-bar"></span>
            <span class="tsh-title">修改建议</span>
            <span class="tsh-sub">SUGGESTIONS</span>
            <span class="tsh-line"></span>
            <span class="tsh-extra">
              <span class="data-readout">{{ suggestionItems.length }}</span>
              <span>条建议</span>
            </span>
          </div>
          <!-- V6.0.4优化：逐条编号渲染建议列表（此前直接插值JSON字符串，观感差且难读） -->
          <div v-if="suggestionItems.length > 0" class="suggestion-list">
            <div v-for="(item, idx) in suggestionItems" :key="idx" class="suggestion-card">
              <span class="hex-badge hex-ghost sg-hex">#{{ idx + 1 }}</span>
              <div class="suggestion-content">
                <div class="suggestion-head">
                  <span v-if="item.legal_basis" class="suggestion-basis">{{ item.legal_basis }}</span>
                  <span class="tech-label">建议条款修订</span>
                </div>
                <p>{{ item.suggestion }}</p>
                <p v-if="item.original_text" class="suggestion-original corner-brackets">原条款：{{ item.original_text }}</p>
              </div>
            </div>
          </div>
          <!-- 无建议时的兜底提示（正常不应出现，防御性兜底） -->
          <div v-else class="suggestion-card">
            <span class="hex-badge hex-ghost sg-hex"><el-icon :size="14"><EditPen /></el-icon></span>
            <p>暂无修改建议，合同整体状况良好；如有疑虑建议咨询执业律师。</p>
          </div>
        </div>

        <!-- AI免责声明（合规提示） -->
        <div class="report-disclaimer report-stagger" style="--stagger-delay: 0.5s">
          <el-icon :size="14"><WarningFilled /></el-icon>
          <span>本审查报告由AI生成，仅供普法参考，不构成律师正式法律意见，重大合同事宜建议咨询执业律师。</span>
        </div>
      </div>
    </el-dialog>

    <!-- ==================== 审查进度对话框 · 菱形流程节点带 ==================== -->
    <el-dialog
      v-model="showReviewProgress"
      :title="reviewStatus === 'success' ? '审查完成' : reviewStatus === 'failed' ? '审查失败' : '合同审查中'"
      width="560px"
      :close-on-click-modal="false"
      :show-close="true"
    >
      <div class="review-progress" :class="reviewStatus === 'pending' ? ['tech-scan', 'scan-always'] : []">
        <!-- 审查结果提示 -->
        <div v-if="reviewStatus === 'success'" class="review-result-tip success">
          <el-icon :size="20"><CircleCheckFilled /></el-icon>
          <span>合同审查已完成，可点击下方「完成关闭」按钮关闭</span>
        </div>
        <div v-else-if="reviewStatus === 'failed'" class="review-result-tip failed">
          <el-icon :size="20"><CircleCloseFilled /></el-icon>
          <span>审查过程中出现异常，可点击「关闭重试」重新发起审查</span>
        </div>
        <!-- 进度条 + 百分比读出 -->
        <div class="progress-row">
          <div class="progress-track">
            <div
              class="progress-fill"
              :style="{ width: reviewProgress + '%' }"
            ></div>
          </div>
          <span class="readout-box progress-readout">
            <span class="data-readout">{{ Math.round(reviewProgress) }}</span>
            <span class="progress-unit">%</span>
          </span>
        </div>
        <!-- 流程节点带：已完成=鎏金实心 / 当前=脉冲呼吸 / 未完成=空心 -->
        <div class="flow-band">
          <div
            v-for="(step, idx) in reviewStepsData"
            :key="idx"
            class="flow-node"
            :class="getStepClass(idx)"
          >
            <span class="diamond-node flow-diamond"></span>
            <div class="step-info">
              <span class="step-name">{{ step.label }}</span>
              <span class="step-desc">{{ step.desc }}</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <!-- 审查中：禁用关闭按钮，等待完成 -->
        <el-button v-if="reviewStatus === 'pending'" disabled>审查进行中...</el-button>
        <!-- 审查失败：关闭重试按钮 -->
        <el-button v-if="reviewStatus === 'failed'" type="warning" @click="handleRetryReview">
          <el-icon><RefreshRight /></el-icon>
          关闭重试
        </el-button>
        <!-- 审查完成：完成关闭按钮 -->
        <el-button v-if="reviewStatus === 'success'" type="primary" @click="handleCloseReviewProgress">
          完成关闭
        </el-button>
      </template>
    </el-dialog>

    <!-- ==================== 评分明细对话框 ==================== -->
    <el-dialog v-model="showScoreDetailDialog" title="合同评分明细" width="620px" destroy-on-close>
      <div v-if="scoredContracts.length > 0" class="score-detail-list">
        <div v-for="c in scoredContracts" :key="c.id" class="score-detail-item corner-brackets">
          <span class="diamond-node sd-node"></span>
          <span class="score-detail-title">{{ c.title }}</span>
          <div class="score-detail-score">
            <el-progress
              type="dashboard"
              :percentage="Math.round(c.overall_score)"
              :width="36"
              :stroke-width="4"
              :color="getScoreColor(c.overall_score)"
            />
          </div>
          <el-tag :type="getRiskLevelType(c.risk_level || '')" size="small" effect="dark">
            {{ c.risk_level || '未评估' }}
          </el-tag>
        </div>
      </div>
      <el-empty v-else description="暂无已审查合同评分数据" />
    </el-dialog>

    <!-- ==================== 分类编辑对话框 ==================== -->
    <el-dialog v-model="showCategoryDialog" title="编辑合同分类" width="420px" destroy-on-close>
      <div v-if="editingCategory" class="category-edit-form">
        <p class="category-contract-name">
          <el-icon><Document /></el-icon>
          {{ editingCategory.title }}
        </p>
        <el-form label-width="80px">
          <el-form-item label="合同分类">
            <el-select v-model="editingCategory.contract_type" placeholder="请选择合同分类" clearable style="width: 100%">
              <el-option v-for="cat in categoryOptions" :key="cat" :label="cat" :value="cat" />
            </el-select>
          </el-form-item>
        </el-form>
        <p class="category-hint">分类标签便于个人合同归档管理，选择空白可清除分类</p>
      </div>
      <template #footer>
        <el-button @click="showCategoryDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCategory">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { contractApi } from '@/api/contract'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

// ==================== 合同列表 ====================
const contracts = ref<any[]>([])
const userStore = useUserStore()
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// ==================== 上传相关 ====================
const showUploadDialog = ref(false)
const isDragging = ref(false)
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement>()

// ==================== 审查报告 ====================
const showReportDialog = ref(false)
const report = ref<any>(null)

// ==================== 审查进度 ====================
const showReviewProgress = ref(false)
const reviewProgress = ref(0)
// 审查状态：pending(进行中) / success(完成) / failed(失败)
const reviewStatus = ref<'pending' | 'success' | 'failed'>('pending')
// 当前审查的合同ID（用于失败重试）
const reviewingContractId = ref<number>(0)
// 审查步骤 - 添加描述文字
const reviewStepsData = [
  { label: '解析合同内容', desc: '正在提取合同文本和结构信息' },
  { label: '完整性检查', desc: '检查合同必要条款是否齐全' },
  { label: '风险检测', desc: '识别潜在风险条款和漏洞' },
  { label: '合规性检查', desc: '对照法律法规验证合规性' },
  { label: '生成报告', desc: '汇总审查结果生成报告' },
]

// ==================== 增强功能：SVG仪表盘 ====================
const gaugeArcLength = Math.PI * 80 // 半圆弧长 ≈ 251.327
const animatedScore = ref(0)
let scoreAnimationTimer: ReturnType<typeof setInterval> | null = null

/** 仪表盘偏移量 - 根据动画分数计算 */
const gaugeOffset = computed(() => {
  return gaugeArcLength * (1 - animatedScore.value / 100)
})

// ==================== 增强功能：风险条款展开/折叠 ====================
const expandedClauses = reactive<Record<number, boolean>>({})

/** 判断条款是否展开（默认展开） */
const isClauseExpanded = (idx: number) => expandedClauses[idx] !== false

/** 切换条款展开/折叠 */
const toggleClause = (idx: number) => {
  expandedClauses[idx] = !isClauseExpanded(idx)
}

// ==================== 增强功能：统计概览 ====================
// 统计口径：已解析(parsed)/已审查(reviewed) 归入「已审查」；已上传(uploaded)/解析中(parsing)/审查中(reviewing) 归入「待审查」
const reviewedCount = computed(() => contracts.value.filter(c => ['parsed', 'reviewed'].includes(c.status)).length)
const pendingCount = computed(() => contracts.value.filter(c => ['uploaded', 'parsing', 'reviewing'].includes(c.status)).length)

// ==================== 统计卡片点击筛选 ====================
// 当前激活的筛选：null=全部, 'reviewed'=已审查, 'pending'=待审查
const activeStatFilter = ref<string | null>(null)

/** 点击统计卡片切换筛选 */
const handleStatClick = (filter: string) => {
  // 平均评分卡片单独处理（弹窗展示明细）
  if (filter === 'score') {
    showScoreDetailDialog.value = true
    return
  }
  // 再次点击同一筛选取消
  activeStatFilter.value = activeStatFilter.value === filter ? null : filter
}

/** 筛选后的合同列表（根据卡片筛选条件过滤） */
const filteredContracts = computed(() => {
  if (!activeStatFilter.value) return contracts.value
  if (activeStatFilter.value === 'reviewed') {
    return contracts.value.filter(c => ['parsed', 'reviewed'].includes(c.status))
  }
  if (activeStatFilter.value === 'pending') {
    return contracts.value.filter(c => ['uploaded', 'parsing', 'reviewing'].includes(c.status))
  }
  return contracts.value
})

// ==================== 评分明细弹窗 ====================
const showScoreDetailDialog = ref(false)
/** 已评分合同列表（用于明细弹窗展示） */
const scoredContracts = computed(() => contracts.value.filter(c => c.overall_score != null))

// 今日剩余合同审查份数（模拟额度，每日重置）
// 实际生产环境应从后端获取用户套餐额度
const remainingQuota = computed(() => {
  const today = new Date().toDateString()
  const usageKey = 'zhifatong_contract_usage'
  try {
    const raw = localStorage.getItem(usageKey)
    const data = raw ? JSON.parse(raw) : { date: '', count: 0 }
    if (data.date !== today) {
      return 10 // 每日上限10份
    }
    return Math.max(0, 10 - data.count)
  } catch {
    return 10
  }
})
const avgScore = computed(() => {
  const scored = contracts.value.filter(c => c.overall_score != null)
  if (scored.length === 0) return '暂无数据'
  return Math.round(scored.reduce((sum: number, c: any) => sum + c.overall_score, 0) / scored.length)
})

// ==================== 增强功能：表格行交错入场 ====================
const tableRowClassName = ({ rowIndex }: { rowIndex: number }) => {
  return `row-stagger row-stagger-${rowIndex % 10}`
}

// ==================== 数据加载 ====================

// 加载合同列表
const loadContracts = async () => {
  try {
    const data = await contractApi.getContractHistory({
      page: currentPage.value,
      page_size: pageSize.value,
    })
    contracts.value = data.items || []
    total.value = data.total || 0
  } catch {
    // 模拟数据
    contracts.value = [
      { id: 1, title: '劳动合同模板', file_name: 'labor_contract.pdf', contract_type: '劳动合同', status: 'reviewed', overall_score: 72, risk_level: '中', created_at: '2024-03-15T10:30:00' },
      { id: 2, title: '采购合同-供应商A', file_name: 'purchase.docx', contract_type: '采购合同', status: 'parsed', overall_score: null, risk_level: null, created_at: '2024-03-14T14:20:00' },
      { id: 3, title: '租赁合同-办公场地', file_name: 'lease.pdf', contract_type: '租赁合同', status: 'uploaded', overall_score: null, risk_level: null, created_at: '2024-03-13T09:00:00' },
    ]
    total.value = 3
  }
}

// 触发文件选择
const triggerFileInput = () => {
  fileInputRef.value?.click()
}

// 处理文件选择
const handleFileSelect = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    selectedFile.value = input.files[0]
  }
}

// 处理拖拽上传
const handleDrop = (e: DragEvent) => {
  isDragging.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files[0]) {
    selectedFile.value = e.dataTransfer.files[0]
  }
}

// 上传合同
const handleUpload = async () => {
  if (!selectedFile.value) return
  // 检查今日剩余额度（管理员不受份数限制，跳过检查）
  if (!userStore.isAdmin && remainingQuota.value <= 0) {
    ElMessage.warning('今日合同审查次数已达上限，请明日再试或升级套餐')
    return
  }
  uploading.value = true
  try {
    await contractApi.uploadContract(selectedFile.value)
    // 记录今日使用次数
    const usageKey = 'zhifatong_contract_usage'
    const today = new Date().toDateString()
    try {
      const raw = localStorage.getItem(usageKey)
      const data = raw ? JSON.parse(raw) : { date: '', count: 0 }
      if (data.date !== today) {
        data.date = today
        data.count = 0
      }
      data.count += 1
      localStorage.setItem(usageKey, JSON.stringify(data))
    } catch {
      // 忽略存储异常
    }
    ElMessage.success('合同上传成功')
    showUploadDialog.value = false
    selectedFile.value = null
    loadContracts()
  } catch {
    ElMessage.error('上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

// 开始审查
const handleReview = async (contractId: number) => {
  reviewingContractId.value = contractId
  showReviewProgress.value = true
  reviewProgress.value = 0
  reviewStatus.value = 'pending'

  // ==================== V6.0.4优化：非线性进度动画 ====================
  // 真实审查（多Agent多次LLM调用）耗时40s+，而旧版进度模拟4s即冲到100%后
  // 僵死等待，观感是"卡住"。改为两段式非线性推进：
  //   阶段1（0→80%）：快速推进，营造即时反馈（约10s，每步递减，逐渐减速）
  //   阶段2（80→90%）：慢速蠕行，最后停在90%等待真实结果，不假装完成
  // 审查请求返回后再跳转100%，确保进度条与真实状态严格一致。
  const interval = setInterval(() => {
    // 阶段2蠕行步长0.5，阶段1基础步长4并随进度衰减（模拟自然减速）
    if (reviewProgress.value < 80) {
      reviewProgress.value = Math.min(80, reviewProgress.value + Math.max(1, 4 - reviewProgress.value * 0.04))
    } else if (reviewProgress.value < 90) {
      reviewProgress.value = Math.min(90, reviewProgress.value + 0.5)
    }
    // 到达90%后自动停止定时器，等待真实完成事件驱动跳100%
    if (reviewProgress.value >= 90) {
      clearInterval(interval)
    }
  }, 250)

  try {
    await contractApi.reviewContract({ contract_id: contractId })
    clearInterval(interval)
    reviewProgress.value = 100
    reviewStatus.value = 'success'
    // 审查完成后刷新表格数据（同步更新统计卡片）
    loadContracts()
  } catch (err: any) {
    clearInterval(interval)
    reviewStatus.value = 'failed'
    // 透传后端具体失败原因（如"该合同正在审查中"/"合同内容为空"），
    // 无具体信息时回退到通用提示，便于用户定位问题而非只看到"请重试"
    const detail = err?.response?.data?.detail
    ElMessage.error(detail ? `审查失败：${detail}` : '审查失败，请重试')
  }
}

/** 关闭审查进度弹窗 */
const handleCloseReviewProgress = () => {
  showReviewProgress.value = false
}

/** 失败后重新审查 */
const handleRetryReview = () => {
  showReviewProgress.value = false
  handleReview(reviewingContractId.value)
}

// 查看报告
const handleViewReport = async (contractId: number) => {
  try {
    const data = await contractApi.getReviewReport(contractId)
    report.value = data
  } catch {
    // 模拟数据
    report.value = {
      overall_score: 72,
      risk_level: '中',
      risk_clause_count: 3,
      review_duration_ms: 8500,
      completeness: '75',
      compliance: '68',
      consistency: '80',
      summary: '该合同整体结构完整，但存在部分条款表述模糊，建议对违约责任和争议解决条款进行补充完善。',
      suggestions: '1. 建议明确违约金计算方式；2. 争议解决条款应增加仲裁选项；3. 保密条款期限建议延长至合同终止后2年。',
      risk_clauses: [
        { clause_title: '第八条 违约责任', clause_content: '如一方违约，应承担违约责任。', risk_level: '高', suggestion: '建议明确违约金计算方式和赔偿范围，避免模糊表述。' },
        { clause_title: '第十二条 争议解决', clause_content: '因本合同引起的争议，双方协商解决。', risk_level: '中', suggestion: '建议增加仲裁条款或明确管辖法院，避免争议解决途径不明确。' },
        { clause_title: '第十五条 保密条款', clause_content: '双方应对合同内容保密。', risk_level: '低', suggestion: '建议明确保密期限和保密范围，增强可执行性。' },
      ],
    }
  }
  showReportDialog.value = true
}

// 删除合同
const handleDelete = async (contractId: number) => {
  try {
    await ElMessageBox.confirm('确认删除该合同及全部审查记录？删除后数据不可恢复', '删除确认', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await contractApi.deleteContract(contractId)
    ElMessage.success('删除成功')
    loadContracts()
  } catch {
    // 用户取消或删除失败
  }
}

// ==================== 优化并下载（V6.0.6新增）===================
/** 正在优化中的合同ID集合（驱动按钮loading态，支持多行并发独立显示） */
const optimizingIds = ref(new Set<number>())

/**
 * 优化并下载处理
 * 调用后端基于审查报告修改建议优化原合同（LLM逐条改写+规则兜底），
 * 返回Markdown全文后以Blob方式触发浏览器下载，文件名为「原合同名_优化后.md」
 */
const handleOptimizeDownload = async (row: any) => {
  if (optimizingIds.value.has(row.id)) return
  optimizingIds.value.add(row.id)
  try {
    const result = await contractApi.optimizeContract(row.id)
    // Blob下载：UTF-8编码（含BOM，确保Excel/记事本正确识别中文）
    const blob = new Blob(['\ufeff' + result.markdown], { type: 'text/markdown;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = result.file_name || `${row.title}_优化后.md`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success(
      `优化完成已开始下载（应用修订${result.replaced_count}/${result.suggestion_count}条），请查看下载文件`
    )
  } catch (err: any) {
    // 透传后端具体原因（未审查/无建议等）
    const detail = err?.response?.data?.detail
    ElMessage.error(detail ? `优化失败：${detail}` : '优化失败，请重试')
  } finally {
    optimizingIds.value.delete(row.id)
  }
}

// ==================== 合同分类编辑 ====================
const showCategoryDialog = ref(false)
const editingCategory = ref<{ id: number; title: string; contract_type: string } | null>(null)
const categoryOptions = ['劳动合同', '采购合同', '租赁合同', '销售合同', '服务合同', '借款合同', '担保合同', '技术转让合同', '其他']

/** 打开分类编辑弹窗 */
const handleEditCategory = (row: any) => {
  editingCategory.value = {
    id: row.id,
    title: row.title,
    contract_type: row.contract_type || '',
  }
  showCategoryDialog.value = true
}

/** 保存分类修改 */
const handleSaveCategory = async () => {
  if (!editingCategory.value) return
  try {
    // 调用后端更新分类（若后端暂未支持则前端本地更新）
    await contractApi.updateContractType(editingCategory.value.id, editingCategory.value.contract_type)
    ElMessage.success('分类修改成功')
    showCategoryDialog.value = false
    loadContracts()
  } catch {
    // 后端暂未支持时，前端本地更新表格数据
    const target = contracts.value.find(c => c.id === editingCategory.value?.id)
    if (target) {
      target.contract_type = editingCategory.value.contract_type || null
    }
    ElMessage.success('分类修改成功')
    showCategoryDialog.value = false
  }
}

// 点击行查看：reviewed状态查看报告，parsed状态可启动审查
const handleRowClick = (row: any) => {
  if (row.status === 'reviewed') {
    handleViewReport(row.id)
  } else if (['uploaded', 'parsed', 'failed'].includes(row.status)) {
    handleReview(row.id)
  }
}

// ==================== 辅助方法 ====================

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    uploaded: 'info',
    parsing: 'warning',
    parsed: 'primary',
    reviewing: 'warning',
    reviewed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    uploaded: '待解析',
    parsing: '解析中',
    parsed: '已解析',
    reviewing: '审查中',
    reviewed: '已审查',
    failed: '审查失败',
  }
  return map[status] || status
}

const getRiskLevelType = (level: string) => {
  const map: Record<string, string> = { '高': 'danger', '中': 'warning', '低': 'success', 'high': 'danger', 'medium': 'warning', 'low': 'success' }
  return map[level] || 'info'
}

/** 获取风险等级CSS类名 - 用于左侧颜色条 */
const getRiskLevelClass = (level: string) => {
  const map: Record<string, string> = { '高': 'high', '中': 'medium', '低': 'low', 'high': 'high', 'medium': 'medium', 'low': 'low' }
  return map[level] || 'medium'
}

const getScoreColor = (score: number) => {
  if (score >= 80) return '#7ca586'
  if (score >= 60) return '#c9973f'
  return '#c05b52'
}

/**
 * 解析维度得分（完整性/合规性/一致性）
 * 兼容三种数据形态（新旧数据并存）：
 * 1. 数值或数字字符串："62.5" / 62.5（V6.0.4后新数据）
 * 2. JSON dict字符串：{"completeness_score":57.1,...}（V6.0.4前旧数据），提取内层分数字段
 * 3. null/undefined：返回0
 * @param val 维度字段值
 * @returns 0-100整数分
 */
const parseDimScore = (val: string | number | null | undefined) => {
  if (val === null || val === undefined || val === '') return 0
  // 数字或数字字符串直接解析
  const num = Number(val)
  if (!isNaN(num)) return Math.round(num)
  // JSON dict字符串：依次尝试提取各分数字段
  try {
    const obj = JSON.parse(String(val))
    if (obj && typeof obj === 'object') {
      // 各维度节点输出的内层字段名（ratio需×100转为百分制）
      const score = obj.completeness_score ?? obj.compliance_score ?? obj.consistency_score ?? obj.score
      if (typeof score === 'number') return Math.round(score)
      const ratio = obj.completeness_ratio
      if (typeof ratio === 'number') return Math.round(ratio * 100)
    }
  } catch {
    // 非JSON内容（如纯文本），忽略
  }
  return 0
}

// ==================== V4.0 多Agent对抗式审查结果计算属性 ====================
// 后端返回的 V4.0 字段为 JSON 字符串，前端需解析后展示

/** 安全解析 JSON 字符串为对象，失败返回默认值 */
const safeParseJson = <T,>(jsonStr: string | null | undefined, defaultValue: T): T => {
  if (!jsonStr) return defaultValue
  try {
    return JSON.parse(jsonStr) as T
  } catch (e) {
    console.warn('[V4.0] JSON解析失败:', e, jsonStr)
    return defaultValue
  }
}

/** 主审Agent识别的风险清单（解析自 report.primary_risks） */
const primaryRisksData = computed<Array<any>>(() =>
  safeParseJson<Array<any>>(report.value?.primary_risks, [])
)

/**
 * 修改建议列表（V6.0.4优化）
 * 后端suggestions为JSON数组字符串，元素形如：
 * { clause_index, original_text, suggestion, legal_basis, issue_type }
 * 兼容旧数据/兜底场景的纯文本建议：包装为单条展示
 * 均无法解析时回退为空（由模板兜底提示渲染）
 */
const suggestionItems = computed<Array<any>>(() => {
  const raw = report.value?.suggestions
  const parsed = safeParseJson<any>(raw, null)
  if (Array.isArray(parsed)) return parsed
  // 解析结果为单个对象（如兜底建议{"suggestion":"..."}）时包装为数组
  if (parsed && typeof parsed === 'object' && parsed.suggestion) return [parsed]
  // 纯文本建议字符串
  if (typeof raw === 'string' && raw.trim()) return [{ suggestion: raw }]
  return []
})

/** 主审风险数量 */
const primaryRisksCount = computed<number>(() => primaryRisksData.value.length)

/** 复核Agent规则复检结果（解析自 report.review_check） */
const reviewCheckData = computed<Record<string, any>>(() =>
  safeParseJson<Record<string, any>>(report.value?.review_check, {})
)

/** 复核确认（approved）数量 */
const reviewApprovedCount = computed<number>(() => reviewCheckData.value.approved_count || 0)

/** 反方Agent反对意见列表（解析自 report.adverse_opinions） */
const adverseOpinionsData = computed<Array<any>>(() =>
  safeParseJson<Array<any>>(report.value?.adverse_opinions, [])
)

/** 对抗辩论记录（解析自 report.debate_log） */
const debateLogData = computed<Array<any>>(() =>
  safeParseJson<Array<any>>(report.value?.debate_log, [])
)

/** 辩论轮数 */
const debateRoundsCount = computed<number>(() => debateLogData.value.length)

/** 未解决问题列表（解析自 report.unresolved_issues） */
const unresolvedIssuesData = computed<Array<any>>(() =>
  safeParseJson<Array<any>>(report.value?.unresolved_issues, [])
)

/** 是否有 V4.0 对抗式审查结果（用于控制区块显示） */
const hasAdversarialReview = computed<boolean>(() => {
  if (!report.value) return false
  // 任一 V4.0 字段有内容即显示
  return (
    primaryRisksCount.value > 0 ||
    adverseOpinionsData.value.length > 0 ||
    debateRoundsCount.value > 0 ||
    (report.value.adverse_opinion_count || 0) > 0
  )
})

const getStepClass = (idx: number) => {
  const step = Math.floor(reviewProgress.value / 20)
  if (idx < step) return 'done'
  if (idx === step) return 'active'
  return 'pending'
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// ==================== 增强功能：仪表盘计数动画 ====================

/** 启动分数计数动画 - 从0递增到目标值 */
const startScoreAnimation = (targetScore: number) => {
  if (scoreAnimationTimer) clearInterval(scoreAnimationTimer)
  animatedScore.value = 0
  const duration = 1500 // 动画总时长1.5秒
  const steps = 60
  const increment = targetScore / steps
  let current = 0
  scoreAnimationTimer = setInterval(() => {
    current += increment
    if (current >= targetScore) {
      animatedScore.value = targetScore
      if (scoreAnimationTimer) clearInterval(scoreAnimationTimer)
    } else {
      animatedScore.value = Math.round(current)
    }
  }, duration / steps)
}

// 监听报告对话框打开，启动仪表盘动画
watch(showReportDialog, (newVal) => {
  if (newVal && report.value) {
    // 延迟启动动画，等待对话框渲染完成
    setTimeout(() => {
      startScoreAnimation(Math.round(report.value.overall_score || 0))
    }, 300)
  } else {
    animatedScore.value = 0
    if (scoreAnimationTimer) clearInterval(scoreAnimationTimer)
  }
})

onMounted(() => {
  loadContracts()
})

onUnmounted(() => {
  if (scoreAnimationTimer) clearInterval(scoreAnimationTimer)
})
</script>

<style scoped lang="scss">
/* ==================================================================
   合同审查页面 · 结构化科技组件体系重构版
   形态语言：tech-frame 矩形科技框架 / diamond 菱形流程节点 /
            hex 六边形徽章 / readout 终端读出 / corner-brackets 角括号
   ================================================================== */

/* ---------- 页面根：网格纹理背景层 + 内容提升 ---------- */
.contract-page {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 20px;

  > *:not(.page-grid-bg) {
    position: relative;
    z-index: 1;
  }
}

/* ==================== 页面头部（结构化区块头形态） ==================== */
.page-header {
  animation: slideInDown 0.45s var(--ease-smooth, ease) both;
}

.page-title-header {
  .page-title-hex {
    width: 30px;
    height: 34px;
    box-shadow: 0 0 16px rgba(70, 96, 140, 0.4);
  }

  .tsh-title {
    font-size: 20px;
    letter-spacing: 2px;
  }

  .header-actions {
    gap: 14px;
  }
}

/* 页面主标题：藏青渐变鎏金文字（缓慢流光） */
.gradient-title {
  background: linear-gradient(120deg, #7c93b5 0%, #5a76a5 35%, #c9a962 100%);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradientShift 5s ease-in-out infinite;
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

/* 额度提示：鎏金终端读出条 */
.quota-hint {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 5px 12px;
  background: rgba(201, 169, 98, 0.06);
  border: 1px solid rgba(201, 169, 98, 0.22);
  box-shadow: inset 3px 0 0 rgba(201, 169, 98, 0.5);

  :deep(.el-icon) {
    color: var(--neon-gold);
  }

  strong {
    color: var(--neon-gold);
    font-weight: 600;
    margin: 0 2px;
    text-shadow: 0 0 10px rgba(201, 169, 98, 0.35);
  }
}

/* shimmer 微光按钮 */
.shimmer-btn {
  position: relative;
  overflow: hidden;
}

.shimmer-overlay {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(148, 158, 178, 0.28), transparent);
  animation: shimmerMove 3s ease-in-out infinite;
  pointer-events: none;
}

@keyframes shimmerMove {
  0% { left: -100%; }
  100% { left: 100%; }
}

/* ==================== 统计概览条：tech-frame + 读出阵列 ==================== */
.stats-bar {
  display: flex;
  align-items: stretch;
  gap: 8px;
  padding: 14px 22px;
  animation: slideInUp 0.5s var(--ease-smooth, ease) 0.05s both;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;

  .stat-value {
    font-size: 24px;
    display: inline-block;
    line-height: 1.1;
  }

  .stat-meta {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  /* 语义色 + 鎏金微光 */
  .stat-success {
    color: #7ca586;
    text-shadow: 0 0 12px rgba(124, 165, 134, 0.35);
  }

  .stat-warning {
    color: #c9973f;
    text-shadow: 0 0 12px rgba(201, 151, 63, 0.35);
  }

  .stat-accent {
    color: var(--text-accent);
    text-shadow: 0 0 12px rgba(90, 118, 165, 0.4);
  }

  /* 可点击卡片：hover 抬升 + 激活态高亮 */
  &.clickable {
    cursor: pointer;
    padding: 8px 4px;
    transition: all 0.25s var(--ease-smooth, ease);

    &:hover {
      background: rgba(70, 96, 140, 0.08);
      transform: translateY(-1px);
    }

    &.active {
      background: rgba(70, 96, 140, 0.12);
      box-shadow: 0 0 0 1px rgba(90, 118, 165, 0.4) inset;
    }
  }
}

/* 自定义状态灯色（青 / 金 / 红） */
.status-light.light-cyan {
  background: var(--neon-cyan);
  box-shadow: 0 0 8px rgba(201, 169, 98, 0.7);
  animation: statusBlink 2.4s ease-in-out infinite;
}

.status-light.light-gold {
  background: var(--neon-gold);
  box-shadow: 0 0 8px rgba(201, 169, 98, 0.7);
  animation: statusBlink 2.4s ease-in-out infinite;
}

.status-light.light-danger {
  background: var(--danger-color);
  box-shadow: 0 0 8px rgba(192, 91, 82, 0.65);
}

@keyframes statusBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
}

.stat-divider {
  width: 1px;
  margin: 4px 6px;
  background: linear-gradient(180deg, transparent, rgba(90, 118, 165, 0.35), transparent);
}

/* ==================== 筛选状态提示条 ==================== */
.filter-hint-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: rgba(201, 169, 98, 0.06);
  border: 1px solid rgba(201, 169, 98, 0.22);
  border-left: 3px solid var(--neon-cyan);
  font-size: 13px;
  color: var(--neon-cyan);
  animation: fadeIn 0.4s ease;

  span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
}

/* ==================== 合同列表：tech-frame 框架形态 ==================== */
.contract-list {
  padding: 18px 20px 20px;
  animation: slideInUp 0.5s var(--ease-smooth, ease) 0.1s both;

  .list-sh {
    margin-bottom: 14px;
  }

  :deep(.el-table) {
    --el-table-bg-color: transparent;
    --el-table-tr-bg-color: transparent;
    --el-table-header-bg-color: transparent;
    --el-table-row-hover-bg-color: rgba(70, 96, 140, 0.06);
  }

  :deep(.el-table__body tr) {
    cursor: pointer;
    /* 交错入场动画 */
    animation: rowSlideIn 0.4s ease-out both;
  }

  /* 行交错延迟 */
  @for $i from 0 through 9 {
    :deep(.row-stagger-#{$i}) {
      animation-delay: #{$i * 0.06}s;
    }
  }

  .score-cell {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* 评分仪表盘入场动画 */
  .score-animate {
    animation: scoreAppear 0.6s ease-out;
  }

  .text-muted {
    color: var(--text-muted);
  }
}

@keyframes rowSlideIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes scoreAppear {
  from { opacity: 0; transform: scale(0.8); }
  to { opacity: 1; transform: scale(1); }
}

/* 行 hover 藏青渐变高亮 */
:deep(.el-table__body tr:hover > td) {
  background: linear-gradient(90deg, rgba(70, 96, 140, 0.08), rgba(201, 169, 98, 0.03)) !important;
}

/* 风险等级标签：鎏金微光 */
.risk-tag-glow {
  box-shadow: 0 0 8px rgba(90, 118, 165, 0.25);
}

:deep(.el-tag--danger.risk-tag-glow) {
  box-shadow: 0 0 10px rgba(192, 91, 82, 0.35);
}

:deep(.el-tag--warning.risk-tag-glow) {
  box-shadow: 0 0 10px rgba(201, 151, 63, 0.35);
}

:deep(.el-tag--success.risk-tag-glow) {
  box-shadow: 0 0 10px rgba(124, 165, 134, 0.35);
}

/* 操作按钮 hover 缩放效果 */
.action-btn {
  transition: transform 0.2s var(--ease-spring, ease);

  &:hover {
    transform: scale(1.05);
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ==================== 上传对话框：tech-frame + 常驻扫描 ==================== */
.upload-area {
  padding: 8px;
  cursor: pointer;
  transition: border-color 0.3s var(--ease-smooth, ease), box-shadow 0.3s var(--ease-smooth, ease);

  &:hover {
    box-shadow: var(--shadow-glow), inset 0 0 30px rgba(70, 96, 140, 0.06);
  }

  /* 拖拽时脉冲发光（青系） */
  &.dragging {
    border-color: rgba(201, 169, 98, 0.6);
    animation: dragPulse 1.5s ease-in-out infinite;
  }
}

@keyframes dragPulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(201, 169, 98, 0.25);
  }
  50% {
    box-shadow: 0 0 24px rgba(201, 169, 98, 0.22), inset 0 0 26px rgba(201, 169, 98, 0.08);
  }
}

/* 扫描内容层 */
.upload-inner {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 34px 24px 28px;
  text-align: center;
}

/* 大图标六边形徽章（悬浮呼吸） */
.upload-hex {
  width: 66px;
  height: 76px;
  margin-bottom: 10px;
  box-shadow: 0 0 24px rgba(70, 96, 140, 0.35);
  animation: hexFloat 3.2s ease-in-out infinite;
}

@keyframes hexFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.upload-text {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 支持格式 chips（切角小片） */
.upload-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
}

.format-chip {
  padding: 3px 12px;
  font-size: 11px;
  letter-spacing: 1px;
  color: var(--neon-cyan-light);
  background: rgba(201, 169, 98, 0.07);
  border: 1px solid rgba(201, 169, 98, 0.25);
  box-shadow: inset 0 0 8px rgba(201, 169, 98, 0.05);
  clip-path: polygon(8px 0, 100% 0, calc(100% - 8px) 100%, 0 100%);
}

/* 拖拽提示行 */
.upload-hint {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 14px;
  font-size: 12px;
  color: var(--text-muted);
}

/* 文件选择后卡片 */
.file-selected-animate {
  animation: fileSelectedIn 0.4s ease-out;
}

@keyframes fileSelectedIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 14px;
  background: rgba(70, 96, 140, 0.08);
  border: 1px solid rgba(90, 118, 165, 0.25);
  font-size: 13px;
  color: var(--text-primary);

  .file-check-icon {
    width: 20px;
    height: 20px;
    animation: checkBounce 0.5s ease-out;

    svg { width: 100%; height: 100%; }
  }

  .remove-file {
    margin-left: auto;
    cursor: pointer;
    color: var(--text-muted);
    transition: color 0.2s ease;

    &:hover { color: var(--danger-color); }
  }
}

@keyframes checkBounce {
  0% { transform: scale(0); }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); }
}

/* 文件选择过渡动画 */
.file-selected-enter-active { transition: all 0.4s ease-out; }
.file-selected-leave-active { transition: all 0.3s ease-in; }
.file-selected-enter-from { opacity: 0; transform: translateY(8px); }
.file-selected-leave-to { opacity: 0; transform: translateY(-8px); }

/* 上传按钮底部渐变进度条（藏青→鎏金） */
.upload-submit-btn {
  position: relative;
  overflow: hidden;
}

.upload-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-color), var(--neon-cyan));
  animation: uploadProgress 2s ease-in-out infinite;
  box-shadow: 0 0 8px rgba(90, 118, 165, 0.5);
}

@keyframes uploadProgress {
  0% { width: 0%; }
  50% { width: 70%; }
  100% { width: 100%; }
}

/* ==================== 审查报告 ==================== */
.report-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 报告入场 stagger 动画 */
.report-stagger {
  opacity: 0;
  animation: reportStaggerIn 0.5s ease-out forwards;
  animation-delay: var(--stagger-delay, 0s);
}

@keyframes reportStaggerIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ---------- 总评面板：终端读出形态 ---------- */
.report-overview {
  position: relative;
  display: flex;
  align-items: center;
  gap: 30px;
  padding: 20px 24px;
  background: linear-gradient(160deg, rgba(23, 29, 42, 0.85), rgba(17, 21, 31, 0.92));
  border: 1px solid var(--border-color);
}

.overview-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 220px;
}

.score-readout {
  padding: 10px 28px;

  /* 大号读出框：放大两侧括号标记 */
  &::before,
  &::after {
    width: 9px;
  }

  &::before {
    border-left-width: 2px;
    border-top-width: 2px;
    border-bottom-width: 2px;
  }

  &::after {
    border-right-width: 2px;
    border-top-width: 2px;
    border-bottom-width: 2px;
  }
}

.score-number {
  font-size: 48px;
  background: linear-gradient(180deg, #ece7da 0%, #7c93b5 55%, #c9a962 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 14px rgba(90, 118, 165, 0.35));
}

.score-unit {
  font-size: 14px;
  color: var(--text-muted);
  margin-left: 6px;
}

.overview-divider {
  width: 1px;
  align-self: stretch;
  background: linear-gradient(180deg, transparent, rgba(90, 118, 165, 0.4), transparent);
}

.overview-details {
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;

  .detail-item {
    display: flex;
    align-items: center;
    gap: 12px;

    .detail-label {
      font-size: 12px;
      letter-spacing: 1px;
      color: var(--text-secondary);
      min-width: 80px;
    }

    .detail-value {
      font-size: 16px;
      color: var(--text-primary);
    }
  }
}

/* ---------- 维度评分：藏青质感轨道 ---------- */
.dimension-scores {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 18px;
  background: rgba(23, 29, 42, 0.5);
  border: 1px solid var(--border-color);

  .dim-sh {
    margin-bottom: 4px;
  }
}

.dimension-item {
  display: flex;
  align-items: center;
  gap: 12px;

  .dim-label {
    font-size: 13px;
    color: var(--text-secondary);
    min-width: 60px;
  }

  /* 藏青质感轨道：内凹阴影 + 十段刻度 */
  .dim-track {
    flex: 1;
    height: 9px;
    position: relative;
    background: linear-gradient(180deg, rgba(60, 74, 104, 0.1), rgba(42, 52, 72, 0.22));
    border: 1px solid rgba(90, 118, 165, 0.22);
    box-shadow: inset 0 1px 4px rgba(8, 10, 16, 0.6), inset 0 0 8px rgba(60, 74, 104, 0.18);
    overflow: hidden;

    &::after {
      content: '';
      position: absolute;
      inset: 0;
      background: repeating-linear-gradient(90deg, transparent 0 calc(10% - 1px), rgba(8, 10, 16, 0.55) calc(10% - 1px) 10%);
      pointer-events: none;
    }
  }

  .dim-fill {
    height: 100%;
    transition: width 1s ease-out;
    position: relative;

    /* 进度头部光晕 */
    &::after {
      content: '';
      position: absolute;
      right: 0;
      top: -2px;
      bottom: -2px;
      width: 12px;
      background: inherit;
      filter: blur(4px);
      opacity: 0.55;
    }
  }

  /* 完整性 - 鎏金渐变（法律权威） */
  .dim-fill-gold {
    background: linear-gradient(90deg, rgba(201, 169, 98, 0.5), #c9a962);
    box-shadow: 0 0 10px rgba(201, 169, 98, 0.3);
  }

  /* 合规性 - 翡翠绿渐变 */
  .dim-fill-green {
    background: linear-gradient(90deg, rgba(124, 165, 134, 0.5), #7ca586);
    box-shadow: 0 0 10px rgba(124, 165, 134, 0.3);
  }

  /* 一致性 - 藏青渐变 */
  .dim-fill-blue {
    background: linear-gradient(90deg, rgba(90, 118, 165, 0.5), #5a76a5);
    box-shadow: 0 0 10px rgba(90, 118, 165, 0.3);
  }

  .dim-value {
    font-size: 12px;
    color: var(--text-secondary);
    min-width: 36px;
    text-align: right;
  }
}

/* ---------- 报告章节通用 ---------- */
.report-section {
  .report-sh {
    margin-bottom: 12px;
  }

  p {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.7;
  }
}

/* 摘要文本块 */
.summary-text {
  position: relative;
  padding: 12px 16px;
  background: rgba(23, 29, 42, 0.5);
  border: 1px solid rgba(90, 118, 165, 0.16);
}

/* ---------- 风险条款卡：菱形节点 + 角括号原文块 ---------- */
.risk-clause-card {
  position: relative;
  padding: 12px 14px;
  margin-bottom: 10px;
  background: linear-gradient(160deg, rgba(23, 29, 42, 0.5), rgba(17, 21, 31, 0.72));
  border: 1px solid rgba(90, 118, 165, 0.16);
  transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s var(--ease-spring, ease);

  &:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-glow);
    transform: translateY(-2px);
  }

  /* 顶部风险等级光带 */
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: rgba(90, 118, 165, 0.3);
  }

  &.risk-level-high::before {
    background: linear-gradient(90deg, transparent, #c05b52, transparent);
    box-shadow: 0 0 10px rgba(192, 91, 82, 0.45);
  }

  &.risk-level-medium::before {
    background: linear-gradient(90deg, transparent, #c9973f, transparent);
    box-shadow: 0 0 10px rgba(201, 151, 63, 0.45);
  }

  &.risk-level-low::before {
    background: linear-gradient(90deg, transparent, #7ca586, transparent);
    box-shadow: 0 0 10px rgba(124, 165, 134, 0.45);
  }

  /* 行首菱形节点按等级着色（高=红系 / 中=鎏金 / 低=绿） */
  .clause-node {
    width: 9px;
    height: 9px;
  }

  &.risk-level-high .clause-node {
    background: linear-gradient(135deg, #e3a9a3, #c05b52);
    box-shadow: 0 0 10px rgba(192, 91, 82, 0.65);
    animation: dangerBreath 2s ease-in-out infinite;
  }

  &.risk-level-medium .clause-node {
    background: linear-gradient(135deg, #dcc489, #c9a962);
    box-shadow: 0 0 9px rgba(201, 169, 98, 0.6);
  }

  &.risk-level-low .clause-node {
    background: linear-gradient(135deg, #8fb398, #7ca586);
    box-shadow: 0 0 9px rgba(124, 165, 134, 0.6);
  }

  .risk-header {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    user-select: none;

    .clause-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      flex: 1;
    }

    &:hover .clause-title {
      color: var(--accent-color);
    }
  }

  /* 条款原文：角括号引用块 */
  .clause-content {
    position: relative;
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.7;
    padding: 10px 16px;
    background: rgba(8, 10, 16, 0.55);
    margin-bottom: 8px;
  }

  /* 角括号随风险等级着色 */
  &.risk-level-high .clause-content::before,
  &.risk-level-high .clause-content::after {
    border-color: rgba(192, 91, 82, 0.6);
  }

  &.risk-level-medium .clause-content::before,
  &.risk-level-medium .clause-content::after {
    border-color: rgba(201, 151, 63, 0.6);
  }

  &.risk-level-low .clause-content::before,
  &.risk-level-low .clause-content::after {
    border-color: rgba(124, 165, 134, 0.6);
  }

  /* 修改建议：鎏金数据光 */
  .clause-suggestion {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 13px;
    color: var(--accent-light);
    padding: 8px 12px;
    background: rgba(201, 169, 98, 0.06);
    border: 1px solid rgba(201, 169, 98, 0.15);
  }
}

/* 高风险节点脉冲 */
@keyframes dangerBreath {
  0%, 100% { box-shadow: 0 0 6px rgba(192, 91, 82, 0.5); }
  50% { box-shadow: 0 0 16px rgba(192, 91, 82, 0.85); }
}

/* 条款展开/折叠箭头 */
.clause-collapse-arrow {
  display: inline-block;
  width: 0;
  height: 0;
  border-left: 5px solid currentColor;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  transition: transform 0.3s ease;
  flex-shrink: 0;

  &.expanded {
    transform: rotate(90deg);
  }
}

/* 条款展开/折叠过渡动画 */
.clause-expand-enter-active,
.clause-expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.clause-expand-enter-from,
.clause-expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.clause-expand-enter-to,
.clause-expand-leave-from {
  opacity: 1;
  max-height: 300px;
}

/* ==================== V4.0 对抗审查：角色面板阵列 ==================== */
.adversarial-section {
  position: relative;
  padding: 18px;
  margin-top: 8px;
  background:
    linear-gradient(rgba(90, 118, 165, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(90, 118, 165, 0.04) 1px, transparent 1px),
    linear-gradient(135deg, rgba(70, 96, 140, 0.09), rgba(201, 169, 98, 0.04));
  background-size: 26px 26px, 26px 26px, cover;
  border: 1px solid rgba(90, 118, 165, 0.3);

  .adversarial-sh {
    margin-bottom: 16px;
  }
}

.adversarial-hex {
  width: 32px;
  height: 36px;
  font-size: 12px;
  letter-spacing: 0.5px;
  box-shadow: 0 0 16px rgba(70, 96, 140, 0.45);
}

.title-info-icon {
  color: var(--text-secondary);
  cursor: help;
  font-size: 14px;
}

/* 红系六边形徽章（未解决） */
.hex-badge.hex-danger {
  background: linear-gradient(135deg, #a04a43, #c05b52);
  color: #fff;
}

/* 红系菱形节点（未解决警示） */
.diamond-node.node-danger {
  background: linear-gradient(135deg, #e3a9a3, #c05b52);
  box-shadow: 0 0 9px rgba(192, 91, 82, 0.6);
}

/* 深砖红菱形节点（反方立场，与红系警示区分） */
.diamond-node.node-pink {
  background: linear-gradient(135deg, #c05b52, #8a453f);
  box-shadow: 0 0 8px rgba(163, 85, 80, 0.55);
}

/* 角色面板阵列 */
.role-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}

.role-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 14px 8px 12px;
  background: linear-gradient(180deg, rgba(23, 29, 42, 0.55), rgba(17, 21, 31, 0.75));
  border: 1px solid rgba(90, 118, 165, 0.16);
  transition: transform 0.3s var(--ease-spring, ease), border-color 0.3s ease, box-shadow 0.3s ease;

  &:hover {
    transform: translateY(-3px);
    border-color: rgba(90, 118, 165, 0.4);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4), 0 0 16px rgba(90, 118, 165, 0.12);
  }

  .role-head {
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .role-hex {
    width: 22px;
    height: 25px;
  }

  .role-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
  }

  .role-readout {
    padding: 2px 16px;
  }

  .role-value {
    font-size: 24px;
  }

  .role-desc {
    font-size: 10px;
    letter-spacing: 1px;
    color: var(--text-muted);
  }
}

/* 角色语义色：主审铜金 / 复核藏青 / 反方砖红 / 辩论鎏金 / 未解决红系 */
.role-primary .role-value {
  color: #7c93b5;
  text-shadow: 0 0 12px rgba(90, 118, 165, 0.4);
}

.role-review .role-value {
  color: #dcc489;
  text-shadow: 0 0 12px rgba(201, 169, 98, 0.4);
}

.role-adverse .role-value {
  color: #c05b52;
  text-shadow: 0 0 12px rgba(192, 91, 82, 0.4);
}

.role-debate .role-value {
  color: #c9a962;
  text-shadow: 0 0 12px rgba(201, 169, 98, 0.4);
}

.role-unresolved {
  border-color: rgba(192, 91, 82, 0.32);

  &:hover {
    border-color: rgba(192, 91, 82, 0.55);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4), 0 0 16px rgba(192, 91, 82, 0.14);
  }
}

.role-unresolved .role-value {
  color: #c05b52;
  text-shadow: 0 0 12px rgba(192, 91, 82, 0.4);
}

/* ---------- 对抗子区块 ---------- */
.adversarial-subsection {
  margin-top: 18px;

  .sub-sh {
    margin-bottom: 10px;
  }

  .sub-sh .tsh-title {
    font-size: 13px;
  }
}

.sub-hex {
  width: 20px;
  height: 23px;
  font-size: 11px;
}

/* 复核结果网格：状态灯 + 读出数字 */
.review-check-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.review-check-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 12px 8px;
  background: rgba(23, 29, 42, 0.6);
  border: 1px solid rgba(90, 118, 165, 0.14);
  box-shadow: inset 0 2px 0 rgba(90, 118, 165, 0.35);
  transition: border-color 0.25s ease;

  &:hover {
    border-color: rgba(90, 118, 165, 0.35);
  }

  .check-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--text-secondary);
  }

  .check-count {
    font-size: 22px;
  }
}

/* 确认=翡翠 / 待争议=琥珀 / 遗漏=红系 */
.review-check-item.approved {
  box-shadow: inset 0 2px 0 #7ca586;

  .check-count { color: #7ca586; }
}

.review-check-item.disputed {
  box-shadow: inset 0 2px 0 #c9973f;

  .check-count { color: #c9973f; }
}

.review-check-item.missed {
  box-shadow: inset 0 2px 0 #c05b52;

  .check-count { color: #c05b52; }
}

/* ---------- 反方意见卡片：砖红光系 + 角括号 ---------- */
.adverse-opinions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.adverse-opinion-card {
  position: relative;
  padding: 10px 14px;
  background: rgba(192, 91, 82, 0.05);
  border: 1px solid rgba(192, 91, 82, 0.2);
  transition: background 0.25s ease, box-shadow 0.25s ease;

  &:hover {
    background: rgba(192, 91, 82, 0.09);
    box-shadow: 0 0 12px rgba(192, 91, 82, 0.12);
  }

  .opinion-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }

  .opposition-text {
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 500;
  }

  .opinion-detail {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
    line-height: 1.5;
  }

  .opinion-detail.demand {
    color: #c9a962;
  }

  .detail-label {
    font-weight: 600;
    color: var(--text-primary);
  }
}

/* ---------- 辩论时间轴：鎏金六边形轮次标记 ---------- */
.debate-timeline {
  position: relative;
  padding-left: 6px;
}

.debate-round {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
  position: relative;
}

/* 轮次间渐变连接线 */
.debate-round:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 13px;
  top: 34px;
  bottom: -12px;
  width: 2px;
  background: linear-gradient(to bottom, rgba(201, 169, 98, 0.45), rgba(201, 169, 98, 0.06));
}

.round-marker {
  flex-shrink: 0;
}

.round-hex {
  width: 28px;
  height: 32px;
  font-size: 12px;
}

.round-content {
  flex: 1;
  padding: 10px 14px;
  background: rgba(23, 29, 42, 0.6);
  border: 1px solid rgba(90, 118, 165, 0.14);
  transition: border-color 0.25s ease;
}

.debate-round:hover .round-content {
  border-color: rgba(90, 118, 165, 0.32);
}

.round-status {
  margin-bottom: 6px;
}

.round-issue {
  font-size: 12px;
  color: #c9a962;
  margin-bottom: 6px;
  font-style: italic;
}

.round-response {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  line-height: 1.6;
  margin-top: 4px;
  color: var(--text-secondary);
}

.resp-node {
  width: 8px;
  height: 8px;
  margin-top: 5px;
}

.round-response .response-label {
  font-weight: 600;
  margin-right: 2px;
}

/* 主审=铜金 / 反方=砖红 */
.primary-response .response-label { color: #5a76a5; }
.adverse-response .response-label { color: #c05b52; }

/* ---------- 未解决警示：红系 ---------- */
.unresolved-warning {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 14px;
  background: rgba(192, 91, 82, 0.07);
  border: 1px solid rgba(192, 91, 82, 0.3);
  box-shadow: inset 3px 0 0 #c05b52, 0 0 14px rgba(192, 91, 82, 0.08);
  font-size: 12px;
  color: #c05b52;
}

.unresolved-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  width: 100%;
}

.unresolved-tag {
  font-size: 11px;
}

/* ==================== 修改建议：六边形编号 + 角括号原文 ==================== */
.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.suggestion-card {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: linear-gradient(160deg, rgba(23, 29, 42, 0.55), rgba(17, 21, 31, 0.8));
  border: 1px solid rgba(90, 118, 165, 0.18);
  transition: border-color 0.3s ease, transform 0.3s var(--ease-spring, ease), box-shadow 0.3s ease;

  /* 悬停高亮：边框亮起 + 上浮 + 藏青微光 */
  &:hover {
    border-color: rgba(90, 118, 165, 0.45);
    transform: translateY(-2px);
    box-shadow: var(--shadow-glow);
  }

  .sg-hex {
    width: 34px;
    height: 38px;
    font-size: 13px;
  }

  /* 建议正文容器（法律依据、建议、原文引用） */
  .suggestion-content {
    flex: 1;
    min-width: 0;

    .suggestion-head {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }

    /* 法律依据标签：鎏金切角小片 */
    .suggestion-basis {
      display: inline-block;
      padding: 2px 10px;
      font-size: 12px;
      color: rgba(201, 169, 98, 0.9);
      background: rgba(201, 169, 98, 0.1);
      border: 1px solid rgba(201, 169, 98, 0.22);
      clip-path: polygon(6px 0, 100% 0, calc(100% - 6px) 100%, 0 100%);
    }

    /* 原文引用：角括号引用块 */
    .suggestion-original {
      position: relative;
      margin-top: 8px;
      font-size: 12px;
      color: var(--text-secondary);
      opacity: 0.75;
      padding: 6px 12px;
      background: rgba(8, 10, 16, 0.5);
    }

    p {
      font-size: 14px;
      color: var(--text-secondary);
      line-height: 1.7;
    }
  }

  /* 兜底卡片（无编号结构） */
  p {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.7;
  }
}

/* ==================== AI 免责声明（琥珀警示光） ==================== */
.report-disclaimer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  margin-top: 4px;
  background: rgba(201, 151, 63, 0.06);
  border: 1px solid rgba(201, 151, 63, 0.22);
  box-shadow: inset 3px 0 0 #c9973f;
  font-size: 12px;
  color: #c9973f;
  font-weight: 500;
  line-height: 1.6;

  :deep(.el-icon) {
    color: #c9973f;
    flex-shrink: 0;
  }
}

/* ==================== 审查进度：菱形流程节点带 ==================== */
.review-result-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  font-size: 13px;

  &.success {
    background: rgba(124, 165, 134, 0.08);
    border: 1px solid rgba(124, 165, 134, 0.25);
    color: #7ca586;
  }

  &.failed {
    background: rgba(192, 91, 82, 0.08);
    border: 1px solid rgba(192, 91, 82, 0.25);
    color: #c05b52;
  }
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 进度条轨道：藏青内凹质感 */
.progress-track {
  flex: 1;
  height: 10px;
  position: relative;
  background: rgba(90, 118, 165, 0.12);
  border: 1px solid rgba(90, 118, 165, 0.22);
  box-shadow: inset 0 1px 4px rgba(8, 10, 16, 0.55);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3c4a68, #5a76a5 55%, #c9a962);
  box-shadow: 0 0 12px rgba(70, 96, 140, 0.45);
  transition: width 0.5s ease;
  position: relative;

  /* 进度头部光晕 */
  &::after {
    content: '';
    position: absolute;
    right: 0;
    top: -3px;
    bottom: -3px;
    width: 16px;
    background: inherit;
    filter: blur(6px);
    opacity: 0.55;
  }
}

.progress-readout {
  .data-readout {
    font-size: 16px;
  }
}

.progress-unit {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 2px;
}

/* 流程节点带 */
.flow-band {
  display: flex;
  margin-top: 22px;
}

.flow-node {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

/* 节点间渐变连接光线 */
.flow-node:not(:first-child)::before {
  content: '';
  position: absolute;
  top: 5px;
  left: calc(-50% + 20px);
  right: calc(50% + 20px);
  height: 1.5px;
  background: linear-gradient(90deg, rgba(201, 169, 98, 0.45), rgba(90, 118, 165, 0.3), rgba(201, 169, 98, 0.45));
}

.flow-node.done:not(:first-child)::before {
  background: linear-gradient(90deg, rgba(201, 169, 98, 0.65), rgba(220, 196, 137, 0.4));
}

.flow-node.pending:not(:first-child)::before {
  background: rgba(90, 118, 165, 0.18);
}

.flow-diamond {
  width: 11px;
  height: 11px;
}

/* 已完成：鎏金实心发光 */
.flow-node.done .flow-diamond {
  background: linear-gradient(135deg, #dcc489, #c9a962);
  box-shadow: 0 0 10px rgba(201, 169, 98, 0.6);
}

/* 当前：脉冲呼吸 */
.flow-node.active .flow-diamond {
  background: linear-gradient(135deg, #dcc489, #c9a962);
  animation: nodeBreath 1.6s ease-in-out infinite;
}

/* 未完成：空心 */
.flow-node.pending .flow-diamond {
  background: transparent;
  border: 1.5px solid rgba(90, 118, 165, 0.55);
  box-shadow: none;
}

@keyframes nodeBreath {
  0%, 100% {
    transform: rotate(45deg) scale(1);
    box-shadow: 0 0 6px rgba(201, 169, 98, 0.4);
  }
  50% {
    transform: rotate(45deg) scale(1.35);
    box-shadow: 0 0 18px rgba(201, 169, 98, 0.85);
  }
}

.step-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  text-align: center;
}

.step-name {
  font-size: 12px;
  color: var(--text-muted);
  transition: color 0.3s ease;
}

.step-desc {
  font-size: 10px;
  line-height: 1.5;
  color: var(--text-muted);
  opacity: 0.7;
}

.flow-node.done .step-name {
  color: var(--success-color);
}

.flow-node.active .step-name {
  color: var(--accent-light);
  font-weight: 600;
}

/* ==================== 评分明细 ==================== */
.score-detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.score-detail-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  background: rgba(23, 29, 42, 0.6);
  border: 1px solid var(--border-color);
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s var(--ease-spring, ease);

  &:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-glow);
    transform: translateY(-2px);
  }

  .sd-node {
    width: 9px;
    height: 9px;
  }

  .score-detail-title {
    flex: 1;
    font-size: 14px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .score-detail-score {
    flex-shrink: 0;
  }
}

/* ==================== 分类编辑表单 ==================== */
.category-edit-form {
  .category-contract-name {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    background: rgba(70, 96, 140, 0.08);
    border: 1px solid var(--border-color);
    box-shadow: inset 3px 0 0 var(--accent-color);
    font-size: 14px;
    color: var(--text-primary);
    margin-bottom: 16px;

    :deep(.el-icon) {
      color: var(--accent-color);
    }
  }

  .category-hint {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 8px;
  }
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .role-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .page-title-header {
    flex-wrap: wrap;

    .tsh-sub {
      display: none;
    }
  }

  .stats-bar {
    flex-wrap: wrap;
    gap: 12px;

    .stat-item {
      flex: 1 1 40%;
    }

    .stat-divider {
      display: none;
    }
  }

  .report-overview {
    flex-direction: column;
    gap: 16px;

    .overview-divider {
      width: 100%;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(90, 118, 165, 0.4), transparent);
    }
  }

  .role-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .review-check-grid {
    grid-template-columns: 1fr;
  }

  .step-desc {
    display: none;
  }
}
</style>
