import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/providers/nl_search_provider.dart';
import '../widgets/search_result_card.dart';

/// Natural Language Search Screen
///
/// Provides AI-powered conversational search for appointments
class NLSearchScreen extends ConsumerStatefulWidget {
  const NLSearchScreen({super.key});

  @override
  ConsumerState<NLSearchScreen> createState() => _NLSearchScreenState();
}

class _NLSearchScreenState extends ConsumerState<NLSearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();

  @override
  void initState() {
    super.initState();

    // Load suggestions and history on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(nlSearchProvider.notifier).loadSuggestions();
      ref.read(nlSearchProvider.notifier).loadHistory();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  void _performSearch() {
    final query = _searchController.text.trim();
    if (query.isNotEmpty) {
      ref.read(nlSearchProvider.notifier).search(query);
      _searchFocusNode.unfocus();
    }
  }

  void _onSuggestionTap(String query) {
    _searchController.text = query;
    _performSearch();
  }

  @override
  Widget build(BuildContext context) {
    final searchState = ref.watch(nlSearchProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Search'),
        elevation: 0,
      ),
      body: Column(
        children: [
          // Search Bar
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: theme.primaryColor.withOpacity(0.05),
              border: Border(
                bottom: BorderSide(
                  color: theme.dividerColor,
                  width: 1,
                ),
              ),
            ),
            child: Column(
              children: [
                // Search Input
                TextField(
                  controller: _searchController,
                  focusNode: _searchFocusNode,
                  decoration: InputDecoration(
                    hintText: 'Ask anything... (e.g., "appointments tomorrow")',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (_searchController.text.isNotEmpty)
                          IconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () {
                              _searchController.clear();
                              ref.read(nlSearchProvider.notifier).clearSearch();
                            },
                          ),
                        IconButton(
                          icon: const Icon(Icons.mic),
                          onPressed: () {
                            // TODO: Integrate with voice input
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Voice input coming soon'),
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    filled: true,
                    fillColor: theme.cardColor,
                  ),
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _performSearch(),
                  onChanged: (value) {
                    // Real-time query parsing for feedback
                    if (value.trim().isNotEmpty) {
                      ref.read(nlSearchProvider.notifier).parseQuery(value);
                    }
                  },
                ),

                // Parsing Feedback (if confidence is low)
                if (searchState.parsedQuery != null &&
                    searchState.parsedQuery!.confidence < 0.7 &&
                    _searchController.text.isNotEmpty &&
                    !searchState.isSearching)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Row(
                      children: [
                        Icon(
                          Icons.info_outline,
                          size: 16,
                          color: theme.colorScheme.secondary,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            searchState.parsedQuery!.clarificationQuestion ??
                                'Try being more specific for better results',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.secondary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),

          // Content
          Expanded(
            child: _buildContent(context, searchState),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(BuildContext context, NLSearchState state) {
    if (state.isSearching) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              state.error!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.red),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => ref.read(nlSearchProvider.notifier).clearError(),
              child: const Text('Dismiss'),
            ),
          ],
        ),
      );
    }

    if (state.results.isNotEmpty) {
      return _buildSearchResults(context, state);
    }

    // Default view: Suggestions and History
    return _buildDefaultView(context, state);
  }

  Widget _buildSearchResults(BuildContext context, NLSearchState state) {
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Summary
        if (state.summary != null)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: theme.primaryColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, color: theme.primaryColor),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        state.summary!,
                        style: theme.textTheme.bodyLarge?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      if (state.searchTimeMs != null)
                        Text(
                          'Search took ${state.searchTimeMs!.toStringAsFixed(0)}ms',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.textTheme.bodySmall?.color?.withOpacity(0.6),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),

        const SizedBox(height: 16),

        // Results
        ...state.results.map((result) => SearchResultCard(result: result)),

        const SizedBox(height: 16),

        // Follow-up Suggestions
        if (state.suggestions.isNotEmpty) ...[
          Text(
            'Try these queries:',
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: state.suggestions
                .map((suggestion) => _SuggestionChip(
                      suggestion: suggestion,
                      onTap: () => _onSuggestionTap(suggestion.text),
                    ))
                .toList(),
          ),
        ],
      ],
    );
  }

  Widget _buildDefaultView(BuildContext context, NLSearchState state) {
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Welcome Message
        Text(
          'Search appointments naturally',
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Ask anything about your appointments in plain language',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.textTheme.bodySmall?.color,
          ),
        ),

        const SizedBox(height: 24),

        // Quick Suggestions
        if (state.suggestions.isNotEmpty) ...[
          Text(
            'Try these:',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: state.suggestions
                .map((suggestion) => _SuggestionChip(
                      suggestion: suggestion,
                      onTap: () => _onSuggestionTap(suggestion.text),
                    ))
                .toList(),
          ),
        ],

        const SizedBox(height: 24),

        // Recent Searches
        if (state.history.isNotEmpty) ...[
          Text(
            'Recent Searches',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          ...state.history.take(5).map((entry) => _HistoryItem(
                entry: entry,
                onTap: () => _onSuggestionTap(entry.query),
              )),
        ],

        const SizedBox(height: 24),

        // Examples
        _buildExamplesSection(context),
      ],
    );
  }

  Widget _buildExamplesSection(BuildContext context) {
    final theme = Theme.of(context);

    final examples = [
      {'icon': '📅', 'text': 'appointments tomorrow'},
      {'icon': '📆', 'text': 'this week\'s schedule'},
      {'icon': '👨‍⚕️', 'text': 'Dr. Sharma\'s appointments'},
      {'icon': '❌', 'text': 'cancelled appointments'},
      {'icon': '👻', 'text': 'no-shows this month'},
      {'icon': '🚨', 'text': 'emergency appointments today'},
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Examples',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),
        ...examples.map((example) => ListTile(
              leading: Text(
                example['icon']!,
                style: const TextStyle(fontSize: 24),
              ),
              title: Text(example['text']!),
              onTap: () => _onSuggestionTap(example['text']!),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            )),
      ],
    );
  }
}

/// Suggestion Chip Widget
class _SuggestionChip extends StatelessWidget {
  final SearchSuggestion suggestion;
  final VoidCallback onTap;

  const _SuggestionChip({
    required this.suggestion,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      avatar: suggestion.icon != null ? Text(suggestion.icon!) : null,
      label: Text(suggestion.text),
      onPressed: onTap,
    );
  }
}

/// History Item Widget
class _HistoryItem extends StatelessWidget {
  final SearchHistoryEntry entry;
  final VoidCallback onTap;

  const _HistoryItem({
    required this.entry,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ListTile(
      leading: CircleAvatar(
        child: Text(entry.categoryIcon),
      ),
      title: Text(entry.query),
      subtitle: Text(
        '${entry.resultCount} result${entry.resultCount != 1 ? 's' : ''} • ${_formatTimestamp(entry.timestamp)}',
        style: theme.textTheme.bodySmall,
      ),
      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
      onTap: onTap,
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);

    if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    } else if (diff.inDays < 7) {
      return '${diff.inDays}d ago';
    } else {
      return DateFormat('MMM d').format(timestamp);
    }
  }
}
