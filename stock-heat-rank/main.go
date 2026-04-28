package main

import (
	"bytes"
	"compress/gzip"
	crand "crypto/rand"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"os"
	"regexp"
	"sort"
	"strings"
	"time"
)

const (
	SKILL_NAME     = "stock-heat-rank"
	SKILL_VERSION  = "1.0.0"
	DEFAULT_API_URL = "https://openapi.iwencai.com/v1/query2data"
	DEFAULT_PAGE    = "1"
	DEFAULT_LIMIT   = "10"
	DEFAULT_TIMEOUT = 30
)

// StockRank 股票排名信息
type StockRank struct {
	Rank      int    `json:"rank"`
	Code      string `json:"code"`
	Name      string `json:"name"`
	HeatScore int    `json:"heat_score"`
	Source    string `json:"source"`
}

// CompositeRank 复合排名
type CompositeRank struct {
	Code           string  `json:"code"`
	Name           string  `json:"name"`
	WencaiRank     int     `json:"wencai_rank"`
	XueqiuRank     int     `json:"xueqiu_rank"`
	EastmoneyRank  int     `json:"eastmoney_rank"`
	CompositeScore float64 `json:"composite_score"`
	AppearCount    int     `json:"appear_count"`
}

// generateTraceID 生成 64 字符十六进制全局唯一追踪 ID
func generateTraceID() string {
	bytes := make([]byte, 32)
	crand.Read(bytes)
	return hex.EncodeToString(bytes)
}

// buildHeaders 构造符合问财网关规范的请求头
func buildHeaders(apiKey, traceID, skillName, skillVersion, callType string) map[string]string {
	return map[string]string{
		"Authorization":       "Bearer " + apiKey,
		"Content-Type":        "application/json",
		"X-Claw-Call-Type":    callType,
		"X-Claw-Skill-Id":     skillName,
		"X-Claw-Skill-Version": skillVersion,
		"X-Claw-Plugin-Id":    "none",
		"X-Claw-Plugin-Version": "none",
		"X-Claw-Trace-Id":     traceID,
	}
}

// getAPIKey 获取问财 API Key
func getAPIKey() string {
	return os.Getenv("IWENCAI_API_KEY")
}

// checkAPIKeyConfigured 检查 API Key 是否已配置
func checkAPIKeyConfigured() bool {
	apiKey := getAPIKey()
	if apiKey == "" {
		return false
	}
	if apiKey == "sk-proj-00" {
		return false
	}
	return true
}

// WencaiOpenAPI 问财官方 OpenAPI 客户端
type WencaiOpenAPI struct {
	apiKey       string
	skillName    string
	skillVersion string
	available    bool
	checked      bool
}

// NewWencaiOpenAPI 创建问财 OpenAPI 客户端
func NewWencaiOpenAPI(skillName, skillVersion string) *WencaiOpenAPI {
	if skillName == "" {
		skillName = SKILL_NAME
	}
	if skillVersion == "" {
		skillVersion = SKILL_VERSION
	}
	return &WencaiOpenAPI{
		apiKey:       getAPIKey(),
		skillName:    skillName,
		skillVersion: skillVersion,
		checked:      false,
	}
}

// IsAvailable 检查 OpenAPI 是否可用
func (api *WencaiOpenAPI) IsAvailable() bool {
	if api.checked {
		return api.available
	}

	if api.apiKey == "" {
		fmt.Println("  [警告] IWENCAI_API_KEY 未配置，OpenAPI 不可用")
		api.available = false
		api.checked = true
		return false
	}

	if api.apiKey == "sk-proj-00" {
		fmt.Println("  [警告] IWENCAI_API_KEY 使用默认占位值，请配置真实的 API Key")
		api.available = false
		api.checked = true
		return false
	}

	api.available = true
	api.checked = true
	return true
}

// Query 执行查询
func (api *WencaiOpenAPI) Query(query string, limit int, callType string) (map[string]interface{}, error) {
	if !api.IsAvailable() {
		return nil, fmt.Errorf("OpenAPI 不可用")
	}

	apiURL := DEFAULT_API_URL
	traceID := generateTraceID()

	payload := map[string]interface{}{
		"query":        query,
		"page":         DEFAULT_PAGE,
		"limit":        fmt.Sprintf("%d", limit),
		"is_cache":     "1",
		"expand_index": "true",
	}

	jsonData, _ := json.Marshal(payload)

	req, err := http.NewRequest("POST", apiURL, bytes.NewReader(jsonData))
	if err != nil {
		return nil, fmt.Errorf("创建请求失败: %v", err)
	}

	headers := buildHeaders(api.apiKey, traceID, api.skillName, api.skillVersion, callType)
	for k, v := range headers {
		req.Header.Set(k, v)
	}

	client := &http.Client{
		Timeout: DEFAULT_TIMEOUT * time.Second,
	}

	fmt.Printf("  使用问财 OpenAPI 查询: %s (trace_id=%s)\n", query, traceID)

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("请求失败: %v", err)
	}
	defer resp.Body.Close()

	fmt.Printf("  API 响应状态码: %d\n", resp.StatusCode)

	body, _ := io.ReadAll(resp.Body)
	bodyStr := string(body)

	if len(bodyStr) == 0 {
		fmt.Println("  [警告] API 返回空响应")
		return nil, fmt.Errorf("空响应")
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		fmt.Printf("  [警告] API 响应不是有效 JSON: %v\n", err)
		if len(bodyStr) < 500 {
			fmt.Printf("  响应内容: %s\n", bodyStr)
		} else {
			fmt.Printf("  响应内容 (前500字符): %s\n", bodyStr[:500])
		}
		return nil, fmt.Errorf("JSON 解析失败: %v", err)
	}

	if statusCode, ok := result["status_code"].(float64); ok && statusCode != 0 {
		statusMsg, _ := result["status_msg"].(string)
		fmt.Printf("  [警告] OpenAPI 返回错误: status_code=%v, msg=%s\n", statusCode, statusMsg)
		return nil, fmt.Errorf("API 返回错误: %s", statusMsg)
	}

	result["trace_id"] = traceID
	return result, nil
}

// WencaiFetcher 问财人气排名采集器
type WencaiFetcher struct {
	openapi *WencaiOpenAPI
}

// NewWencaiFetcher 创建问财采集器
func NewWencaiFetcher() *WencaiFetcher {
	return &WencaiFetcher{
		openapi: NewWencaiOpenAPI("", ""),
	}
}

// Fetch 获取问财人气排名
func (f *WencaiFetcher) Fetch(top int) ([]StockRank, error) {
	fmt.Println("【问财】正在采集...")

	if !f.openapi.IsAvailable() {
		return nil, fmt.Errorf("OpenAPI 不可用")
	}

	query := fmt.Sprintf("人气排名前%d", top)
	result, err := f.openapi.Query(query, top, "normal")
	if err != nil {
		return nil, err
	}

	return f.parseResult(result, top), nil
}

func (f *WencaiFetcher) parseResult(result map[string]interface{}, top int) []StockRank {
	ranks := make([]StockRank, 0)

	datas, ok := result["datas"].([]interface{})
	if !ok {
		return ranks
	}

	for i, item := range datas {
		if i >= top {
			break
		}

		data, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		code := getStrVal(data, "股票代码", "code", "stockCode")
		name := getStrVal(data, "股票简称", "name", "stockName")

		if code != "" && name != "" {
			codeStr := code
			if dotIdx := strings.Index(codeStr, "."); dotIdx != -1 {
				codeStr = codeStr[:dotIdx]
			}

			ranks = append(ranks, StockRank{
				Code:      codeStr,
				Name:      name,
				Rank:      i + 1,
				HeatScore: top - i,
				Source:    "wencai",
			})
		}
	}

	return ranks
}

// XueqiuFetcher 雪球热榜采集器
type XueqiuFetcher struct {
	client *http.Client
}

// NewXueqiuFetcher 创建雪球采集器
func NewXueqiuFetcher() *XueqiuFetcher {
	return &XueqiuFetcher{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Fetch 获取雪球热榜A股前50
func (f *XueqiuFetcher) Fetch() ([]StockRank, error) {
	html, err := f.fetchPage()
	if err != nil {
		return nil, err
	}

	ranks := f.parseFromHTML(html)
	if len(ranks) == 0 {
		return nil, fmt.Errorf("未能从页面解析到股票数据")
	}

	return ranks, nil
}

func (f *XueqiuFetcher) fetchPage() (string, error) {
	url := "https://xueqiu.com/hot/stock"

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("创建请求失败: %v", err)
	}

	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")
	req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9")
	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

	resp, err := f.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("请求失败: %v", err)
	}
	defer resp.Body.Close()

	var reader io.Reader = resp.Body
	if resp.Header.Get("Content-Encoding") == "gzip" {
		gzReader, err := gzip.NewReader(resp.Body)
		if err != nil {
			return "", fmt.Errorf("解压gzip失败: %v", err)
		}
		defer gzReader.Close()
		reader = gzReader
	}

	body, err := io.ReadAll(reader)
	if err != nil {
		return "", fmt.Errorf("读取响应失败: %v", err)
	}

	return string(body), nil
}

func (f *XueqiuFetcher) parseFromHTML(html string) []StockRank {
	ranks := make([]StockRank, 0)

	pattern := regexp.MustCompile(`"name":"([^"]+)","value":[^}]*"symbol":"(SH|SZ)(\d+)"`)
	matches := pattern.FindAllStringSubmatch(html, -1)

	seen := make(map[string]bool)

	for _, match := range matches {
		if len(match) < 4 {
			continue
		}

		name := match[1]
		market := match[2]
		code := match[3]

		fullCode := market + code
		if seen[fullCode] {
			continue
		}
		seen[fullCode] = true

		if code != "" && name != "" && len(ranks) < 50 {
			ranks = append(ranks, StockRank{
				Code:      code,
				Name:      name,
				Rank:      len(ranks) + 1,
				HeatScore: 100 - len(ranks),
				Source:    "xueqiu",
			})
		}
	}

	return ranks
}

// EastmoneyFetcher 东方财富人气排名采集器
type EastmoneyFetcher struct {
	client *http.Client
}

// NewEastmoneyFetcher 创建东财采集器
func NewEastmoneyFetcher() *EastmoneyFetcher {
	return &EastmoneyFetcher{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Fetch 获取东方财富人气排名前50
func (f *EastmoneyFetcher) Fetch() ([]StockRank, error) {
	return f.getRankData()
}

func (f *EastmoneyFetcher) getRankData() ([]StockRank, error) {
	url := "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"

	postData := map[string]interface{}{
		"appId":         "stockrank",
		"globalId":      "786e4c21-70dc-435a-93bb-38",
		"marketType":    "",
		"rankType":      "1",
		"pageNo":        1,
		"pageSize":      100,
		"fromDate":      "",
		"toDate":        "",
		"stockIndustry": "",
		"stockCode":     "",
		"stockName":     "",
		"clientSource":  "web",
		"clientVersion": "1.0.0",
	}

	jsonData, _ := json.Marshal(postData)

	req, err := http.NewRequest("POST", url, bytes.NewReader(jsonData))
	if err != nil {
		return nil, fmt.Errorf("创建请求失败: %v", err)
	}

	req.Header.Set("Accept", "*/*")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")
	req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9")
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Origin", "https://vipmoney.eastmoney.com")
	req.Header.Set("Referer", "https://vipmoney.eastmoney.com/")
	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

	resp, err := f.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("请求失败: %v", err)
	}
	defer resp.Body.Close()

	var reader io.Reader = resp.Body
	if resp.Header.Get("Content-Encoding") == "gzip" {
		gzReader, err := gzip.NewReader(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("解压gzip失败: %v", err)
		}
		defer gzReader.Close()
		reader = gzReader
	}

	body, err := io.ReadAll(reader)
	if err != nil {
		return nil, fmt.Errorf("读取响应失败: %v", err)
	}

	return f.parseResponse(body)
}

func (f *EastmoneyFetcher) parseResponse(body []byte) ([]StockRank, error) {
	var result struct {
		Status int `json:"status"`
		Data   []struct {
			Sc string `json:"sc"`
			Rk int    `json:"rk"`
		} `json:"data"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("解析失败: %v", err)
	}

	if result.Status != 0 {
		return nil, fmt.Errorf("API返回错误: status=%d", result.Status)
	}

	ranks := make([]StockRank, 0)

	for _, item := range result.Data {
		code := item.Sc
		if len(code) < 8 {
			continue
		}

		code = code[2:]

		if len(ranks) >= 50 {
			break
		}

		ranks = append(ranks, StockRank{
			Code:      code,
			Name:      "",
			Rank:      item.Rk,
			HeatScore: 100 - len(ranks),
			Source:    "eastmoney",
		})
	}

	return ranks, nil
}

func getStrVal(m map[string]interface{}, keys ...string) string {
	for _, key := range keys {
		if v, ok := m[key]; ok {
			if s, ok := v.(string); ok {
				return s
			}
		}
	}
	return ""
}

func randString(n int) string {
	const letters = "abcdefghijklmnopqrstuvwxyz0123456789"
	b := make([]byte, n)
	for i := range b {
		b[i] = letters[rand.Intn(len(letters))]
	}
	return string(b)
}

func normalizeCode(code string) string {
	if len(code) == 6 {
		return validateAStockCode(code)
	}
	if len(code) == 8 && (code[:2] == "SH" || code[:2] == "SZ") {
		return validateAStockCode(code[2:])
	}
	if len(code) == 9 && (code[6:] == ".SH" || code[6:] == ".SZ") {
		return validateAStockCode(code[:6])
	}
	return ""
}

func validateAStockCode(code string) string {
	if len(code) != 6 {
		return ""
	}
	for _, c := range code {
		if c < '0' || c > '9' {
			return ""
		}
	}
	first := code[0]
	if first != '6' && first != '0' && first != '3' && first != '8' && first != '4' {
		return ""
	}
	return code
}

func calculateComposite(wencai, xueqiu, eastmoney []StockRank) []CompositeRank {
	stockMap := make(map[string]*CompositeRank)

	for _, r := range wencai {
		code := normalizeCode(r.Code)
		if code == "" {
			continue
		}
		if _, ok := stockMap[code]; !ok {
			stockMap[code] = &CompositeRank{
				Code: code,
				Name: r.Name,
			}
		}
		stockMap[code].WencaiRank = r.Rank
		stockMap[code].AppearCount++
	}

	for _, r := range xueqiu {
		code := normalizeCode(r.Code)
		if code == "" {
			continue
		}
		if _, ok := stockMap[code]; !ok {
			stockMap[code] = &CompositeRank{
				Code: code,
				Name: r.Name,
			}
		}
		stockMap[code].XueqiuRank = r.Rank
		stockMap[code].AppearCount++
	}

	for _, r := range eastmoney {
		code := normalizeCode(r.Code)
		if code == "" {
			continue
		}
		if _, ok := stockMap[code]; !ok {
			stockMap[code] = &CompositeRank{
				Code: code,
				Name: r.Name,
			}
		}
		if stockMap[code].Name == "" && r.Name != "" {
			stockMap[code].Name = r.Name
		}
		stockMap[code].EastmoneyRank = r.Rank
		stockMap[code].AppearCount++
	}

	for _, stock := range stockMap {
		score := 0.0

		if stock.WencaiRank > 0 {
			score += float64(100 - stock.WencaiRank)
		}
		if stock.XueqiuRank > 0 {
			score += float64(100 - stock.XueqiuRank)
		}
		if stock.EastmoneyRank > 0 {
			score += float64(100 - stock.EastmoneyRank)
		}

		if stock.AppearCount == 2 {
			score += 20
		} else if stock.AppearCount == 3 {
			score += 50
		}

		stock.CompositeScore = score / 3.5
	}

	ranks := make([]CompositeRank, 0, len(stockMap))
	for _, stock := range stockMap {
		ranks = append(ranks, *stock)
	}

	sort.Slice(ranks, func(i, j int) bool {
		return ranks[i].CompositeScore > ranks[j].CompositeScore
	})

	return ranks
}

func printTable(ranks []CompositeRank, top int) {
	fmt.Println()
	fmt.Println("┌──────┬──────────┬────────────┬──────┬──────┬──────┬──────────┬──────┐")
	fmt.Println("│ 排名 │   代码   │    名称    │ 问财 │ 雪球 │ 东财 │  热度分  │ 出现 │")
	fmt.Println("├──────┼──────────┼────────────┼──────┼──────┼──────┼──────────┼──────┤")

	for i, r := range ranks {
		if i >= top {
			break
		}

		wc := "-"
		if r.WencaiRank > 0 {
			wc = fmt.Sprintf("%d", r.WencaiRank)
		}
		xq := "-"
		if r.XueqiuRank > 0 {
			xq = fmt.Sprintf("%d", r.XueqiuRank)
		}
		em := "-"
		if r.EastmoneyRank > 0 {
			em = fmt.Sprintf("%d", r.EastmoneyRank)
		}

		fmt.Printf("│ %4d │ %-8s │ %-10s │ %4s │ %4s │ %4s │ %8.1f │ %4d │\n",
			i+1, r.Code, r.Name, wc, xq, em, r.CompositeScore, r.AppearCount)
	}

	fmt.Println("└──────┴──────────┴────────────┴──────┴──────┴──────┴──────────┴──────┘")
	fmt.Println()
}

func printJSON(ranks []CompositeRank, top int) {
	result := make([]CompositeRank, 0)
	for i, r := range ranks {
		if i >= top {
			break
		}
		result = append(result, r)
	}
	jsonData, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(jsonData))
}

func printAPIKeyReminder() {
	fmt.Println("=")
	fmt.Println("⚠️  问财 API Key 未配置！")
	fmt.Println("=")
	fmt.Println()
	fmt.Println("需要配置 IWENCAI_API_KEY 环境变量才能使用问财人气排名查询功能。")
	fmt.Println()
	fmt.Println("配置方式：")
	fmt.Println("1. Windows (CMD):")
	fmt.Println("   set IWENCAI_API_KEY=your_api_key_here")
	fmt.Println()
	fmt.Println("2. Windows (PowerShell):")
	fmt.Println("   $env:IWENCAI_API_KEY=\"your_api_key_here\"")
	fmt.Println()
	fmt.Println("3. Linux/Mac:")
	fmt.Println("   export IWENCAI_API_KEY=your_api_key_here")
	fmt.Println()
	fmt.Println("获取 API Key：请访问同花顺问财开放平台申请")
	fmt.Println()
}

func main() {
	top := flag.Int("top", 50, "获取前N名")
	format := flag.String("format", "table", "输出格式: table, json")
	flag.Parse()

	fmt.Println("=== 股票热度排名采集器 ===")
	fmt.Printf("采集时间: %s\n\n", time.Now().Format("2006-01-02 15:04:05"))

	if !checkAPIKeyConfigured() {
		fmt.Println("=")
		fmt.Println("⚠️  警告：问财 API Key 未配置")
		fmt.Println("=")
		printAPIKeyReminder()
		fmt.Println("问财人气排名功能将无法使用")
		fmt.Println("将只使用雪球和东方财富的数据进行计算")
		fmt.Println("=")
		fmt.Println()
	}

	// 采集问财数据
	wencaiRanks := make([]StockRank, 0)
	wencaiFetcher := NewWencaiFetcher()
	ranks, err := wencaiFetcher.Fetch(50)
	if err != nil {
		fmt.Printf("【问财】采集失败: %v\n", err)
	} else {
		wencaiRanks = ranks
		fmt.Printf("【问财】成功获取 %d 只股票\n", len(wencaiRanks))
	}

	// 采集雪球数据
	fmt.Println("\n【雪球】正在采集...")
	xueqiuRanks := make([]StockRank, 0)
	xueqiuFetcher := NewXueqiuFetcher()
	ranks, err = xueqiuFetcher.Fetch()
	if err != nil {
		fmt.Printf("  采集失败: %v\n", err)
	} else {
		xueqiuRanks = ranks
		fmt.Printf("  成功获取 %d 只A股\n", len(xueqiuRanks))
	}

	// 采集东财数据
	fmt.Println("\n【东财】正在采集...")
	eastmoneyRanks := make([]StockRank, 0)
	eastmoneyFetcher := NewEastmoneyFetcher()
	ranks, err = eastmoneyFetcher.Fetch()
	if err != nil {
		fmt.Printf("  采集失败: %v\n", err)
	} else {
		eastmoneyRanks = ranks
		fmt.Printf("  成功获取 %d 只股票\n", len(eastmoneyRanks))
	}

	// 计算复合热度
	fmt.Println("\n=== 复合热度排名 ===")
	fmt.Printf("问财: %d | 雪球: %d | 东财: %d\n", len(wencaiRanks), len(xueqiuRanks), len(eastmoneyRanks))

	result := calculateComposite(wencaiRanks, xueqiuRanks, eastmoneyRanks)

	switch *format {
	case "json":
		printJSON(result, *top)
	default:
		printTable(result, *top)
	}
}
